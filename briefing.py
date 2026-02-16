"""Main orchestrator - runs the full morning briefing pipeline."""

import os
import json
import subprocess
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from run_triage import run_triage
from collectors.cal import get_today, get_tomorrow
from compose import compose_briefing
from audio import generate_audio
from feed import create_or_update_feed
from publish import publish

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(PROJECT_DIR, "state.json")


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {"last_run": None, "episode_count": 0}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def open_spotify():
    """Open Spotify on macOS."""
    subprocess.run(["open", "-a", "Spotify"], check=False)


def run(skip_triage=False, skip_publish=False, open_player=True):
    """Run the full briefing pipeline.

    Args:
        skip_triage: If True, read the latest existing triage note instead of running /triage.
        skip_publish: If True, generate audio but don't push to GitHub.
        open_player: If True, open Spotify after generating.
    """
    state = load_state()
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")

    print(f"=== Morning Briefing - {now.strftime('%A %-d %B %Y')} ===\n")

    # Step 1: Run triage (or use existing)
    if skip_triage:
        from pathlib import Path
        triage_dir = "/Users/freddiechambers/Library/Mobile Documents/iCloud~md~obsidian/Documents/iCloud/4. Notes/Morning Triage"
        files = sorted(Path(triage_dir).glob("*.md"), key=lambda f: f.stat().st_mtime, reverse=True)
        if not files:
            raise RuntimeError("No triage notes found")
        triage_path = str(files[0])
        print(f"Using existing triage: {os.path.basename(triage_path)}")
    else:
        print("Running triage...")
        triage_path = run_triage()

    # Step 2: Collect data
    print("Collecting calendar events...")
    today_events = get_today()
    tomorrow_events = get_tomorrow()
    print(f"  Today: {len(today_events)} events, Tomorrow: {len(tomorrow_events)} events")

    # Step 3: Claude writes the podcast script (searches vault for context, enriches, synthesises)
    print("Claude is writing your briefing script...")
    script = compose_briefing(triage_path, today_events, tomorrow_events)
    print(f"  {len(script.split())} words, {len(script)} characters")
    print(f"\n--- SCRIPT ---\n{script}\n--- END ---\n")

    # Step 4: Generate audio
    episode_filename = f"{date_str}.mp3"
    print("Generating audio...")
    audio_path = generate_audio(script, episode_filename)

    # Step 5: Update RSS feed
    episode_title = f"Briefing - {now.strftime('%-d %b %Y')}"
    file_size = os.path.getsize(audio_path)
    create_or_update_feed(
        episode_filename,
        episode_title,
        script[:200] + "...",
        episode_date=now,
        file_size_bytes=file_size,
    )

    # Step 6: Publish
    if not skip_publish:
        print("Publishing to GitHub Pages...")
        publish(audio_path)
    else:
        print("Skipping publish (--skip-publish)")

    # Step 7: Update state
    state["last_run"] = now.isoformat()
    state["episode_count"] = state.get("episode_count", 0) + 1
    save_state(state)

    # Step 8: Open Spotify
    if open_player:
        print("Opening Spotify...")
        open_spotify()

    print(f"\nDone! Episode #{state['episode_count']}: {episode_filename}")
    return audio_path


if __name__ == "__main__":
    import sys
    skip_triage = "--skip-triage" in sys.argv
    skip_publish = "--skip-publish" in sys.argv
    no_open = "--no-open" in sys.argv
    run(skip_triage=skip_triage, skip_publish=skip_publish, open_player=not no_open)
