"""Use parallel research agents + composer to write an enriched podcast script."""

import os
from datetime import datetime
from pathlib import Path

from agents import run_research_and_compose

SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "scripts")


def compose_briefing(triage_note_path, today_events, tomorrow_events, target_date=None):
    """Call Claude to write an enriched podcast script.

    Args:
        triage_note_path: Path to the triage note markdown file.
        today_events: List of calendar event dicts for today.
        tomorrow_events: List of calendar event dicts for tomorrow.
        target_date: The date the briefing is for (defaults to today).

    Returns:
        The script text (plain spoken word).
    """
    now = datetime.now()
    if target_date is None:
        target_date = now
    date_str = target_date.strftime("%A %-d %B %Y")

    # Read the full triage note
    with open(triage_note_path, "r") as f:
        triage_content = f.read()

    # Format calendar events
    today_cal = _format_events(today_events, "today")
    tomorrow_cal = _format_events(tomorrow_events, "tomorrow")

    # Run parallel research agents + composer
    script = run_research_and_compose(triage_content, today_cal, tomorrow_cal, date_str)

    # Save the script as a markdown file for reference
    os.makedirs(SCRIPTS_DIR, exist_ok=True)
    script_filename = target_date.strftime("%Y-%m-%d") + ".md"
    script_path = os.path.join(SCRIPTS_DIR, script_filename)
    with open(script_path, "w") as f:
        f.write(f"# Morning Briefing Script - {date_str}\n\n")
        f.write(script)
    print(f"Script saved: {script_path}")

    return script


def _format_events(events, label):
    """Format calendar events for the prompt."""
    if not events:
        return f"No events {label}."

    lines = []
    for e in events:
        if e["is_all_day"]:
            lines.append(f"- {e['title']} (all day)")
        else:
            loc = f" @ {e['location']}" if e.get("location") else ""
            lines.append(f"- {e['start']}-{e['end']} {e['title']}{loc} ({e['duration_mins']}min)")
    return "\n".join(lines)


if __name__ == "__main__":
    # Test with latest triage and real calendar
    from collectors.cal import get_today, get_tomorrow
    from collectors.triage import parse_triage

    vault = "/Users/freddiechambers/Library/Mobile Documents/iCloud~md~obsidian/Documents/iCloud"
    triage_dir = os.path.join(vault, "4. Notes", "Morning Triage")
    latest = max(Path(triage_dir).glob("*.md"), key=lambda f: f.stat().st_mtime)

    print(f"Using triage: {latest.name}")
    print("Fetching calendar...")
    today = get_today()
    tomorrow = get_tomorrow()
    print(f"Today: {len(today)} events, Tomorrow: {len(tomorrow)} events")

    print("Writing script via Claude...")
    script = compose_briefing(str(latest), today, tomorrow)
    print(f"\n--- SCRIPT ({len(script.split())} words) ---\n")
    print(script)
