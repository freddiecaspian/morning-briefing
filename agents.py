"""Parallel research agents + composer for the morning briefing pipeline.

Runs three specialist agents in parallel (people, project, calendar),
then feeds their research into a composer agent that writes the final script.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

VAULT = "/Users/freddiechambers/Library/Mobile Documents/iCloud~md~obsidian/Documents/iCloud"
FALLBACK_MESSAGE = "[UNAVAILABLE - this research agent timed out or failed. Write the briefing without this section.]"

log = logging.getLogger("morning-briefing.agents")


# ---------------------------------------------------------------------------
# Shared helper
# ---------------------------------------------------------------------------

def _call_claude(prompt: str, system_prompt: str, tools: str | None = None,
                 timeout: int = 120) -> str:
    """Call Claude CLI as a subprocess. Returns stdout text."""
    cmd = [
        "claude", "-p", prompt,
        "--system-prompt", system_prompt,
        "--dangerously-skip-permissions",
    ]
    if tools:
        cmd.extend(["--allowedTools", tools])

    result = subprocess.run(
        cmd,
        cwd=VAULT,
        capture_output=True,
        text=True,
        timeout=timeout,
    )

    if result.returncode != 0:
        raise RuntimeError(f"Claude call failed: {result.stderr[:500]}")

    return result.stdout.strip()


# ---------------------------------------------------------------------------
# People Agent
# ---------------------------------------------------------------------------

PEOPLE_SYSTEM_PROMPT = """You are a research assistant preparing context about PEOPLE for a morning briefing podcast.

You will receive a triage note and calendar events. Your job:

1. Extract every person name mentioned in the triage tasks AND calendar events.
2. For each person, search the vault to find:
   - Who they are (role, relationship, organisation)
   - Last interaction or note mentioning them
   - Any open threads, pending actions, or shared projects
3. Search in: 4. Notes/, 5. Sources/, 15. Transcripts/

OUTPUT FORMAT - write clear prose sections, one per person:

PERSON: [Full Name]
Context: [Who they are, how Freddie knows them]
Last interaction: [Date and what happened]
Open threads: [Any pending actions involving this person]
---

If you find nothing in the vault for a person, still list them with "No vault context found."

Be thorough but concise. Do NOT write a podcast script. Just deliver the research.
Skip generic calendar entries with no named people (e.g. "Lecture", "Tutorial").
Focus on people where vault context will genuinely add value to the briefing."""


def people_agent(triage_content: str, today_cal: str, tomorrow_cal: str) -> str:
    """Research vault context for every person mentioned in triage + calendar."""
    prompt = f"""Here are today's inputs. Extract all person names and research each one in the vault.

TRIAGE NOTE:
{triage_content}

CALENDAR - TODAY:
{today_cal}

CALENDAR - TOMORROW:
{tomorrow_cal}

Search the vault now and return your findings."""

    return _call_claude(prompt, PEOPLE_SYSTEM_PROMPT, tools="Read,Glob,Grep", timeout=180)


# ---------------------------------------------------------------------------
# Project Agent
# ---------------------------------------------------------------------------

PROJECT_SYSTEM_PROMPT = """You are a research assistant preparing context about PROJECTS AND TASKS for a morning briefing podcast.

You will receive a triage note containing active tasks and projects. Your job:

1. Identify every distinct project or task in the triage note.
2. For each one, search the vault to find:
   - Related notes, drafts, or previous work (check 4. Notes/, 5. Sources/)
   - How long the task has been active (look for earlier triage notes in 4. Notes/Morning Triage/)
   - Any dependencies or blockers mentioned in related notes
   - Relevant deadlines or context from linked notes
3. Pay special attention to tasks marked as "carrying forward" - count how many triage versions they have appeared in.

OUTPUT FORMAT - write clear prose sections, one per project:

PROJECT: [Task/Project Name]
Status: [active/keen/urgent/quick-win]
Age: [How long it has been in triage, if discoverable]
Vault context: [Related notes found, key details]
Dependencies: [What blocks this or what this blocks]
---

Be thorough but concise. Do NOT write a podcast script. Just deliver the research.
Prioritise projects marked urgent or active. Quick wins need less depth."""


def project_agent(triage_content: str) -> str:
    """Research vault context for every project/task in the triage note."""
    prompt = f"""Here is today's triage note. Identify all projects and tasks, then search the vault for context on each.

TRIAGE NOTE:
{triage_content}

Search the vault now and return your findings."""

    return _call_claude(prompt, PROJECT_SYSTEM_PROMPT, tools="Read,Glob,Grep", timeout=180)


# ---------------------------------------------------------------------------
# Calendar Agent
# ---------------------------------------------------------------------------

CALENDAR_SYSTEM_PROMPT = """You are a research assistant analysing CALENDAR LOGISTICS for a morning briefing podcast.

You will receive today's and tomorrow's calendar events. Your job:

1. Identify scheduling issues:
   - Back-to-back events with no break (flag if gap < 15 mins)
   - Events in different locations that require travel time
   - Suspiciously empty blocks before known deadlines
   - Double-bookings or overlapping time slots
   - Very long days (first event to last event > 10 hours)

2. Identify preparation needs:
   - Events that likely need prep (meetings, presentations, calls)
   - Deadlines falling on the same day as packed schedules

3. Spot patterns:
   - Is tomorrow much busier than today? Flag it.
   - Are there good blocks of free time for deep work?
   - Any evening commitments that limit the working day?

OUTPUT FORMAT - write clear prose sections:

SCHEDULE OVERVIEW:
[Brief summary of today vs tomorrow density]

CONFLICTS AND RISKS:
[Each issue on its own line with specific times]

PREPARATION NEEDED:
[Events that need advance prep, with suggested timing]

FREE BLOCKS:
[Windows of unscheduled time, with suggested uses]

---

Be specific with times. Do NOT write a podcast script. Just deliver the analysis.
If the calendar is light, say so briefly - don't pad the analysis."""


def calendar_agent(today_cal: str, tomorrow_cal: str) -> str:
    """Analyse calendar for conflicts, gaps, and logistics."""
    prompt = f"""Analyse these calendar events for scheduling issues, conflicts, and logistics.

CALENDAR - TODAY:
{today_cal}

CALENDAR - TOMORROW:
{tomorrow_cal}

Return your analysis now."""

    return _call_claude(prompt, CALENDAR_SYSTEM_PROMPT, tools=None, timeout=60)


# ---------------------------------------------------------------------------
# Composer Agent
# ---------------------------------------------------------------------------

COMPOSER_SYSTEM_PROMPT = """You are Lily, writing Freddie's personal morning briefing podcast script.

PERSONALITY:
- Directness: 90 - Lead with what matters. No throat-clearing, no preambles.
- Warmth: 70 - Like a sharp friend who knows his life. Not a life coach.
- Formality: 15 - Very casual. Contractions. Spoken rhythm.
- Precision: 90 - Specific times, names, actions. Never vague.
- Composure: 85 - Confident. No hedging. Just say it.
- Expressiveness: 70 - Editorial voice. Connect dots, offer perspective.
- Optimism: 55 - Realistic. If tomorrow is packed, say so. End on what's achievable.
- Enthusiasm: 50 - Interested, not performatively excited.
- Challenge: 65 - Flag things lingering too long. Honest, not nagging.
- Brevity: 90 - Every sentence earns its place or gets cut.
- Playfulness: 40 - Occasional dry wit. Never forced.
- Deference: 30 - Has opinions, states them. Doesn't argue.

You will receive:
1. Today's triage note (tasks, priorities, context)
2. Today's and tomorrow's calendar events
3. Three research packets (people, project, calendar analysis)

Write a SHORT conversational podcast script (400-600 words, 2-3 minutes spoken) that Freddie listens to on his way to class.

RULES:
- Open with the date and one orienting line. No "good morning, here's your briefing" filler.
- Synthesise, don't list. "3 lectures starting at noon" not each one separately.
- Prioritise ruthlessly. First thing you say = most important thing today.
- USE research packets to add insight: who people are, how long tasks have been lingering, conflicts.
- Weave research in naturally. Don't repeat it verbatim.
- Group calendar events, mention gaps, flag back-to-backs.
- Flag duplicates or overlapping tasks directly.
- Quick wins punchy: "Knock out these 3 before your first lecture."
- Closers crisp and actionable. Not "Have a wonderful day!"
- Write ONLY spoken script. No markdown, headings, stage directions, emojis, hashtags, wikilinks.
- Times spoken naturally: "half twelve" not "12:30", "quarter to four" not "15:45".
- If a research packet is UNAVAILABLE, work without it. Don't mention it."""


def composer_agent(triage_content: str, today_cal: str, tomorrow_cal: str,
                   people_report: str, project_report: str, calendar_report: str,
                   date_str: str) -> str:
    """Write the final podcast script from triage + calendar + research packets."""
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

PEOPLE RESEARCH:

{people_report}

---

PROJECT RESEARCH:

{project_report}

---

CALENDAR ANALYSIS:

{calendar_report}

---

Now write the podcast script. Remember: 400-600 words, warm and direct, spoken word only."""

    return _call_claude(prompt, COMPOSER_SYSTEM_PROMPT, tools=None, timeout=120)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def run_research_and_compose(triage_content: str, today_cal: str,
                             tomorrow_cal: str, date_str: str) -> str:
    """Run three research agents in parallel, then compose the final script.

    Args:
        triage_content: Raw text of the triage note.
        today_cal: Formatted calendar string for today.
        tomorrow_cal: Formatted calendar string for tomorrow.
        date_str: Human-readable date string.

    Returns:
        The final podcast script text.
    """
    results = {
        "people": FALLBACK_MESSAGE,
        "project": FALLBACK_MESSAGE,
        "calendar": FALLBACK_MESSAGE,
    }

    agent_tasks = {
        "people": (people_agent, (triage_content, today_cal, tomorrow_cal)),
        "project": (project_agent, (triage_content,)),
        "calendar": (calendar_agent, (today_cal, tomorrow_cal)),
    }

    print("  Launching research agents (people, project, calendar)...")

    with ThreadPoolExecutor(max_workers=3) as executor:
        future_to_name = {}
        for name, (fn, args) in agent_tasks.items():
            future = executor.submit(fn, *args)
            future_to_name[future] = name

        for future in as_completed(future_to_name):
            name = future_to_name[future]
            try:
                results[name] = future.result(timeout=190)
                log.info(f"{name} agent completed ({len(results[name])} chars)")
                print(f"  {name} agent done ({len(results[name])} chars)")
            except subprocess.TimeoutExpired:
                log.warning(f"{name} agent timed out")
                print(f"  {name} agent timed out (using fallback)")
            except Exception as e:
                log.warning(f"{name} agent failed: {e}")
                print(f"  {name} agent failed: {e} (using fallback)")

    succeeded = [k for k, v in results.items() if v != FALLBACK_MESSAGE]
    failed = [k for k, v in results.items() if v == FALLBACK_MESSAGE]
    if failed:
        log.warning(f"Agents failed: {failed}. Composing with: {succeeded}")
    print(f"  Research complete. Succeeded: {succeeded}. Writing script...")

    script = composer_agent(
        triage_content=triage_content,
        today_cal=today_cal,
        tomorrow_cal=tomorrow_cal,
        people_report=results["people"],
        project_report=results["project"],
        calendar_report=results["calendar"],
        date_str=date_str,
    )

    return script


# ---------------------------------------------------------------------------
# CLI for standalone testing
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from pathlib import Path
    from datetime import datetime

    logging.basicConfig(level=logging.INFO)

    triage_dir = os.path.join(VAULT, "4. Notes", "Morning Triage")
    latest = max(Path(triage_dir).glob("*.md"), key=lambda f: f.stat().st_mtime)

    with open(latest, "r") as f:
        triage = f.read()

    print(f"Using triage: {latest.name}")

    sample_cal = "No events."

    if "--people" in sys.argv:
        print("=== PEOPLE AGENT ===")
        print(people_agent(triage, sample_cal, sample_cal))
    elif "--project" in sys.argv:
        print("=== PROJECT AGENT ===")
        print(project_agent(triage))
    elif "--calendar" in sys.argv:
        print("=== CALENDAR AGENT ===")
        print(calendar_agent(
            "- 12:00-13:00 UDJ Tutorial (60min)\n- 14:00-16:00 Financial Markets (120min)",
            "- 09:00-10:30 Strategy Lecture @ Doriot (90min)\n- 14:00-16:00 AI Club (120min)",
        ))
    elif "--compose" in sys.argv:
        print("=== FULL PIPELINE ===")
        script = run_research_and_compose(
            triage, sample_cal, sample_cal,
            datetime.now().strftime("%A %-d %B %Y"),
        )
        print(f"\n--- SCRIPT ({len(script.split())} words) ---\n")
        print(script)
    else:
        print("Usage: python agents.py [--people|--project|--calendar|--compose]")
