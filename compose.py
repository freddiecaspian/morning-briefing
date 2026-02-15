"""Use Claude to write an enriched podcast script from triage + calendar + vault context."""

import subprocess
import json
import os
from datetime import datetime
from pathlib import Path

VAULT = "/Users/freddiechambers/Library/Mobile Documents/iCloud~md~obsidian/Documents/iCloud"
SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "scripts")

SYSTEM_PROMPT = """You are a podcast script writer for Freddie's personal morning briefing.

You will receive:
1. Today's triage note (tasks, priorities, context)
2. Today's calendar events
3. Tomorrow's calendar events

Your job is to write a SHORT, conversational podcast script (target 400-600 words, 2-3 minutes spoken) that Freddie listens to on his way to class.

RULES:
- Write in a warm, direct tone. Like a sharp friend who knows your life inside out.
- DO NOT read out raw task lists. Synthesise. "You've got 3 lectures today starting at noon" not a list of each one.
- Prioritise ruthlessly. What ACTUALLY matters today? Lead with that.
- Add genuine insight: spot conflicts, flag prep needed, connect dots between tasks.
- For calendar: group similar events, mention gaps, flag back-to-backs.
- For tasks: what's truly urgent vs what can wait? What's the smart order to tackle things?
- If you notice duplicates or overlapping tasks, call it out.
- Keep quick wins punchy: "Knock out these 3 before your first lecture."
- The closer should feel human, not robotic.
- Write ONLY the spoken script. No markdown, no headings, no stage directions.
- No emojis. No hashtags. No wikilinks. Pure spoken word.
- Times should be spoken naturally: "half twelve" not "12:30", "quarter to four" not "15:45".
- DO NOT say things like "paragraph" or "section" - this is speech, not text."""


def compose_briefing(triage_note_path, today_events, tomorrow_events):
    """Call Claude to write an enriched podcast script.

    Args:
        triage_note_path: Path to the triage note markdown file.
        today_events: List of calendar event dicts for today.
        tomorrow_events: List of calendar event dicts for tomorrow.

    Returns:
        The script text (plain spoken word).
    """
    now = datetime.now()
    date_str = now.strftime("%A %-d %B %Y")

    # Read the full triage note
    with open(triage_note_path, "r") as f:
        triage_content = f.read()

    # Format calendar events
    today_cal = _format_events(today_events, "today")
    tomorrow_cal = _format_events(tomorrow_events, "tomorrow")

    # Build the prompt
    prompt = f"""Write a morning briefing podcast script for Freddie.

Date: {date_str}

---

TRIAGE NOTE (today's tasks, priorities, and context):

{triage_content}

---

CALENDAR - TODAY:

{today_cal}

---

CALENDAR - TOMORROW:

{tomorrow_cal}

---

Search Freddie's vault (in 4. Notes/, 5. Sources/, 15. Transcripts/) for any related context that would enrich the briefing. Look for notes related to the active tasks, upcoming meetings, or people mentioned. Cross-reference and add useful context.

Now write the podcast script. Remember: 400-600 words, warm and direct, spoken word only."""

    # Call Claude CLI
    result = subprocess.run(
        [
            "claude",
            "-p",
            prompt,
            "--system-prompt", SYSTEM_PROMPT,
            "--allowedTools", "Read,Glob,Grep",
            "--dangerously-skip-permissions",
        ],
        cwd=VAULT,
        capture_output=True,
        text=True,
        timeout=180,  # 3 min max
    )

    if result.returncode != 0:
        raise RuntimeError(f"Claude script writing failed: {result.stderr[:500]}")

    script = result.stdout.strip()

    # Save the script as a markdown file for reference
    os.makedirs(SCRIPTS_DIR, exist_ok=True)
    script_filename = now.strftime("%Y-%m-%d") + ".md"
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
    from collectors.calendar import get_today, get_tomorrow
    from collectors.triage import parse_triage

    triage_dir = os.path.join(VAULT, "4. Notes", "Morning Triage")
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
