"""Publish an FMV podcast script to ElevenLabs and the RSS feed.

Usage:
    python fmv_publish.py <vault_file_path> [episode_title]

Example:
    python fmv_publish.py "/path/to/19. INSEAD/FMV - Bonds Podcast Script.md"
    python fmv_publish.py "/path/to/file.md" "FMV - Bonds"
    python fmv_publish.py "/path/to/file.md" --skip-publish
"""

import os
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

from audio import generate_audio, DEFAULT_VOICE, DEFAULT_MODEL, API_KEY, EPISODES_DIR
from feed import create_or_update_feed
from publish import publish

# ElevenLabs API limit - 10,000 chars per request
CHUNK_LIMIT = 9_500


def extract_script(file_path):
    """Extract plain-text script from the ## Script section of a podcast note."""
    text = Path(file_path).read_text(encoding="utf-8")

    match = re.search(r"^## Script\s*\n(.*?)(?=^## |\Z)", text, re.MULTILINE | re.DOTALL)
    if not match:
        raise ValueError(f"No '## Script' section found in {file_path}")

    script = match.group(1).strip()

    # Strip markdown so TTS reads clean prose
    script = re.sub(r"^#{1,6}\s+", "", script, flags=re.MULTILINE)   # headings
    script = re.sub(r"\*\*(.+?)\*\*", r"\1", script)                  # bold
    script = re.sub(r"\*(.+?)\*", r"\1", script)                      # italic
    script = re.sub(r"`(.+?)`", r"\1", script)                        # inline code
    script = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", script)               # links
    script = re.sub(r"^[-*>]\s+", "", script, flags=re.MULTILINE)     # bullets / blockquotes
    script = re.sub(r"\n{3,}", "\n\n", script)                        # excess blank lines

    return script.strip()


def split_into_chunks(text, max_chars=CHUNK_LIMIT):
    """Split text into chunks at sentence boundaries, each under max_chars.

    Splits at '. ', '! ', '? ' to avoid cutting mid-sentence.
    """
    if len(text) <= max_chars:
        return [text]

    chunks = []
    remaining = text

    while len(remaining) > max_chars:
        # Find the last sentence boundary before the limit
        slice_ = remaining[:max_chars]
        # Look for sentence end markers going backwards
        cut = max(
            slice_.rfind(". "),
            slice_.rfind("! "),
            slice_.rfind("? "),
            slice_.rfind("\n\n"),
        )
        if cut == -1:
            # No sentence boundary found - hard cut at max_chars
            cut = max_chars - 1

        chunks.append(remaining[:cut + 1].strip())
        remaining = remaining[cut + 1:].strip()

    if remaining:
        chunks.append(remaining)

    return chunks


def generate_audio_chunked(text, output_filename):
    """Generate audio for long text by chunking and concatenating MP3 bytes.

    ElevenLabs has a 10,000 char limit per request. For long scripts we
    split into chunks, generate each separately, and concatenate the raw
    MP3 bytes. MPEG frames are self-contained so byte concatenation is
    valid and plays correctly in all podcast apps.
    """
    from elevenlabs import ElevenLabs

    if not API_KEY:
        raise RuntimeError("ELEVENLABS_API_KEY not set in .env")

    chunks = split_into_chunks(text)
    print(f"  Split into {len(chunks)} chunks ({[len(c) for c in chunks]} chars each)")

    client = ElevenLabs(api_key=API_KEY)
    os.makedirs(EPISODES_DIR, exist_ok=True)
    output_path = os.path.join(EPISODES_DIR, output_filename)

    with open(output_path, "wb") as out_f:
        for i, chunk in enumerate(chunks):
            print(f"  Generating chunk {i + 1}/{len(chunks)} ({len(chunk)} chars)...")
            audio_gen = client.text_to_speech.convert(
                text=chunk,
                voice_id=DEFAULT_VOICE,
                model_id=DEFAULT_MODEL,
                output_format="mp3_44100_128",
            )
            for mp3_bytes in audio_gen:
                out_f.write(mp3_bytes)

    # Zero out all Info/Xing VBR headers in the concatenated file.
    # Each ElevenLabs chunk has its own VBR header claiming the file is only
    # that chunk's duration long. Without this fix, podcast players stop after
    # the first chunk. Zeroing them forces players to scan all MPEG frames.
    _fix_concatenated_mp3(output_path)

    size_kb = os.path.getsize(output_path) / 1024
    print(f"  Audio saved: {output_path} ({size_kb:.0f} KB)")
    return output_path


def _fix_concatenated_mp3(filepath):
    """Fix a concatenated multi-chunk MP3 so it plays at full length.

    When ElevenLabs chunks are concatenated each chunk contributes:
      1. An ID3 tag (metadata header)
      2. An MPEG frame containing a Xing/Info VBR header claiming the file
         is only that chunk's duration long

    Podcast players hit the first VBR header and stop after chunk 1 (~10 min).
    Interior ID3 tags at chunk boundaries can also cause players to treat the
    file as a new stream and stop.

    Fix:
      Step 1 - Zero all Xing/Info VBR markers so players scan all MPEG frames.
      Step 2 - Strip interior ID3 tags (keep only the first one).
    """
    with open(filepath, "rb") as f:
        data = bytearray(f.read())
    file_size = len(data)

    # Step 1: Zero all Xing/Info VBR headers
    vbr_count = 0
    i = 0
    while i < file_size - 4:
        if data[i:i+4] in (b"Info", b"Xing"):
            data[i:i+4] = b"\x00\x00\x00\x00"
            vbr_count += 1
        i += 1

    # Step 2: Find and strip interior ID3 tags
    def _id3_size(d, pos):
        """Parse syncsafe integer to get total ID3 tag size including header."""
        flags = d[pos + 5]
        raw = d[pos+6:pos+10]
        size = ((raw[0] & 0x7f) << 21 | (raw[1] & 0x7f) << 14 |
                (raw[2] & 0x7f) << 7 | (raw[3] & 0x7f))
        has_footer = bool(flags & 0x10)
        return 10 + size + (10 if has_footer else 0)

    # Find all plausible ID3 tags (skip false positives where size > file)
    id3s = []
    i = 0
    while True:
        idx = data.find(b"ID3", i)
        if idx == -1:
            break
        if idx + 10 <= file_size:
            sz = _id3_size(data, idx)
            if sz < file_size:
                id3s.append((idx, sz))
        i = idx + 1

    # Rebuild file stripping all ID3 tags except the first
    if len(id3s) > 1:
        segments = []
        prev_end = 0
        for pos, sz in id3s[1:]:
            segments.append(bytes(data[prev_end:pos]))
            prev_end = pos + sz
        segments.append(bytes(data[prev_end:]))
        data = bytearray(b"".join(segments))

    with open(filepath, "wb") as f:
        f.write(data)

    print(f"  Fixed {os.path.basename(filepath)}: zeroed {vbr_count} VBR header(s), "
          f"stripped {len(id3s) - 1} interior ID3 tag(s)")


def episode_filename_from_path(file_path):
    """Derive an MP3 filename from the vault file path.

    E.g. "FMV - Bonds Podcast Script.md" → "fmv-bonds-2026-02-28.mp3"
    """
    stem = Path(file_path).stem
    stem = stem.replace("Podcast Script", "").strip()
    stem = stem.replace(" - ", "-").replace(" ", "-")
    stem = unicodedata.normalize("NFKD", stem)
    stem = "".join(c for c in stem if c.isalnum() or c == "-")
    stem = stem.lower()
    date_str = datetime.now().strftime("%Y-%m-%d")
    return f"{stem}-{date_str}.mp3"


def episode_title_from_path(file_path):
    """Derive a human-readable episode title from the vault file path."""
    return Path(file_path).stem.replace(" Podcast Script", "")


def run(file_path, title=None, skip_publish=False):
    """Full pipeline: extract script → TTS (chunked) → feed → publish."""
    file_path = str(Path(file_path).expanduser().resolve())
    print(f"Source: {file_path}")

    # 1. Extract
    print("Extracting script...")
    script = extract_script(file_path)
    word_count = len(script.split())
    char_count = len(script)
    print(f"  {word_count} words / {char_count} chars (~{word_count // 150} min)")

    # 2. Generate audio (chunked for long scripts)
    episode_filename = episode_filename_from_path(file_path)
    episode_title = title or episode_title_from_path(file_path)
    print(f"Generating audio → {episode_filename}")
    audio_path = generate_audio_chunked(script, episode_filename)

    # 3. Update RSS feed
    print("Updating feed...")
    file_size = os.path.getsize(audio_path)
    # Estimate duration: ~150 words per minute at natural speaking pace
    duration_seconds = (word_count / 150) * 60
    create_or_update_feed(
        episode_filename,
        episode_title,
        script[:200] + "...",
        episode_date=datetime.now(),
        file_size_bytes=file_size,
        duration_seconds=duration_seconds,
    )

    # 4. Publish
    if not skip_publish:
        print("Publishing to GitHub Pages...")
        publish(audio_path, commit_message=f"Add FMV episode: {episode_title}")
    else:
        print(f"Skipping publish. Audio at: {audio_path}")

    print(f"\nDone! '{episode_title}' published as {episode_filename}")
    return audio_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    vault_file = sys.argv[1]
    custom_title = next((a for a in sys.argv[2:] if not a.startswith("--")), None)
    skip = "--skip-publish" in sys.argv

    run(vault_file, title=custom_title, skip_publish=skip)
