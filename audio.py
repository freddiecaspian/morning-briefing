"""Generate audio from text using ElevenLabs TTS API."""

import os
from pathlib import Path
from dotenv import load_dotenv
from elevenlabs import ElevenLabs

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

API_KEY = os.getenv("ELEVENLABS_API_KEY")
EPISODES_DIR = os.path.join(os.path.dirname(__file__), "episodes")

# Default voice - "Lily" British female voice. Using voice ID directly to avoid needing voices_read permission.
DEFAULT_VOICE = "pFZP5JQG7iQjIQuC4Bku"  # Lily
DEFAULT_MODEL = "eleven_multilingual_v2"


def generate_audio(text, output_filename, voice=DEFAULT_VOICE, model=DEFAULT_MODEL):
    """Send text to ElevenLabs TTS and save the MP3.

    Args:
        text: The briefing script to convert to speech.
        output_filename: Filename for the MP3 (e.g. "2026-02-15.mp3").
        voice: ElevenLabs voice name or ID.
        model: ElevenLabs model ID.

    Returns:
        Full path to the saved MP3 file.
    """
    if not API_KEY:
        raise RuntimeError("ELEVENLABS_API_KEY not set in .env")

    client = ElevenLabs(api_key=API_KEY)

    os.makedirs(EPISODES_DIR, exist_ok=True)
    output_path = os.path.join(EPISODES_DIR, output_filename)

    audio_generator = client.text_to_speech.convert(
        text=text,
        voice_id=voice,
        model_id=model,
        output_format="mp3_44100_128",
    )

    # Write the audio stream to file
    with open(output_path, "wb") as f:
        for chunk in audio_generator:
            f.write(chunk)

    size_kb = os.path.getsize(output_path) / 1024
    print(f"Audio saved: {output_path} ({size_kb:.0f} KB)")
    return output_path


def _resolve_voice(client, voice_name):
    """Resolve a voice name to its ID."""
    # If it looks like an ID already, return it
    if len(voice_name) > 15 and not " " in voice_name:
        return voice_name

    # Search for the voice by name
    voices = client.voices.get_all()
    for v in voices.voices:
        if v.name.lower() == voice_name.lower():
            return v.voice_id

    raise ValueError(f"Voice '{voice_name}' not found. Available: {[v.name for v in voices.voices]}")


if __name__ == "__main__":
    test_text = "Good morning Freddie. This is a test of the morning briefing audio system. If you can hear this clearly, everything is working."
    path = generate_audio(test_text, "test.mp3")
    print(f"Test audio at: {path}")
