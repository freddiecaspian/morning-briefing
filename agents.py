"""Parallel research agents + composer for the morning briefing pipeline.

Runs five specialist agents in parallel (people, 3x project, calendar),
then merges project results and feeds everything into a composer agent
that writes the final script.
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
# Project Agents (3 focused sub-agents, run in parallel)
# ---------------------------------------------------------------------------

PROJECT_STATUS_SYSTEM_PROMPT = """You are a research assistant doing a QUICK STATUS ANALYSIS of tasks for a morning briefing podcast.

You will receive a triage note. Your job (NO vault searching needed):

1. Extract every distinct project/task from the triage note.
2. Categorise each one: urgent, active, keen, quick-win, or deferred.
3. Spot duplicates or overlapping tasks (e.g. two tasks that are really the same thing).
4. Identify which tasks are quick wins (< 15 min, no dependencies).
5. Flag any tasks that seem vague or missing a clear next action.

OUTPUT FORMAT:

TASK OVERVIEW:
[Total count, breakdown by category]

DUPLICATES/OVERLAPS:
[Any tasks that look like they're the same thing, or closely related]

QUICK WINS:
[Tasks that could be knocked out fast, with suggested grouping]

ATTENTION NEEDED:
[Vague tasks, tasks with no clear next step, anything that looks stuck]
---

Be concise. Do NOT write a podcast script. Just deliver the analysis.
Do NOT search the vault - work only from the triage note itself."""


def project_status_agent(triage_content: str) -> str:
    """Quick status analysis of tasks - no vault search, pure triage analysis."""
    prompt = f"""Analyse this triage note. Categorise tasks, spot duplicates, identify quick wins.

TRIAGE NOTE:
{triage_content}

Return your analysis now."""

    return _call_claude(prompt, PROJECT_STATUS_SYSTEM_PROMPT, tools=None, timeout=120)


PROJECT_HISTORY_SYSTEM_PROMPT = """You are a research assistant checking TRIAGE HISTORY for a morning briefing podcast.

You will receive a triage note with today's tasks. Your job:

1. Extract the key task/project names from the triage note.
2. Search ONLY the folder 4. Notes/Morning Triage/ for recent triage notes (last 14 days).
3. For each task, count how many previous triages it appeared in.
4. Flag tasks that have been carrying forward for more than 3 consecutive triages without progress.

OUTPUT FORMAT - one line per task:

TASK: [Name] — appeared in [N] of last [M] triages. [First seen: date if discoverable]
TASK: [Name] — NEW (not in previous triages)
...

LINGERING TASKS (3+ consecutive triages):
[List any tasks that have been sitting too long, with the count]
---

Be concise. Only search 4. Notes/Morning Triage/. Do NOT search the broader vault."""


def project_history_agent(triage_content: str) -> str:
    """Check how long each task has been in triage by scanning Morning Triage folder."""
    prompt = f"""Check how long each task in this triage has been carrying forward.

TRIAGE NOTE:
{triage_content}

Search 4. Notes/Morning Triage/ for recent triage notes and count appearances. Return your findings."""

    return _call_claude(prompt, PROJECT_HISTORY_SYSTEM_PROMPT, tools="Read,Glob,Grep", timeout=180)


PROJECT_CONTEXT_SYSTEM_PROMPT = """You are a research assistant finding VAULT CONTEXT for projects mentioned in a morning briefing podcast.

You will receive a triage note. Your job:

1. Extract the key project/task names from the triage note.
2. Search 4. Notes/ and 5. Sources/ for related notes, drafts, or previous work.
3. For each project where you find something, note:
   - What related notes exist
   - Key details or context from those notes
   - Any dependencies or blockers mentioned
   - Relevant deadlines

OUTPUT FORMAT - one section per project where you found context:

PROJECT: [Name]
Related notes: [What you found]
Key context: [Important details]
Dependencies: [If any]
---

Skip projects where you find nothing in the vault - don't pad with "nothing found" entries.
Be concise. Do NOT search Morning Triage/ (another agent handles that).
Do NOT write a podcast script. Just deliver the research."""


def project_context_agent(triage_content: str) -> str:
    """Search vault for related notes and context per project."""
    prompt = f"""Find vault context for the projects in this triage note.

TRIAGE NOTE:
{triage_content}

Search 4. Notes/ and 5. Sources/ for related notes. Return your findings."""

    return _call_claude(prompt, PROJECT_CONTEXT_SYSTEM_PROMPT, tools="Read,Glob,Grep", timeout=180)


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

    return _call_claude(prompt, CALENDAR_SYSTEM_PROMPT, tools=None, timeout=120)


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
    """Run five research agents in parallel, then compose the final script.

    Agents: people, calendar, project_status, project_history, project_context.
    The three project sub-agents are merged into one project report for the composer.

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
        "project_status": FALLBACK_MESSAGE,
        "project_history": FALLBACK_MESSAGE,
        "project_context": FALLBACK_MESSAGE,
        "calendar": FALLBACK_MESSAGE,
    }

    agent_tasks = {
        "people": (people_agent, (triage_content, today_cal, tomorrow_cal)),
        "project_status": (project_status_agent, (triage_content,)),
        "project_history": (project_history_agent, (triage_content,)),
        "project_context": (project_context_agent, (triage_content,)),
        "calendar": (calendar_agent, (today_cal, tomorrow_cal)),
    }

    print("  Launching research agents (people, 3x project, calendar)...")

    with ThreadPoolExecutor(max_workers=2) as executor:
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

    # Merge the 3 project sub-agent results into one report
    project_sections = []
    if results["project_status"] != FALLBACK_MESSAGE:
        project_sections.append(f"STATUS ANALYSIS:\n{results['project_status']}")
    if results["project_history"] != FALLBACK_MESSAGE:
        project_sections.append(f"TRIAGE HISTORY:\n{results['project_history']}")
    if results["project_context"] != FALLBACK_MESSAGE:
        project_sections.append(f"VAULT CONTEXT:\n{results['project_context']}")

    project_report = "\n\n---\n\n".join(project_sections) if project_sections else FALLBACK_MESSAGE

    script = composer_agent(
        triage_content=triage_content,
        today_cal=today_cal,
        tomorrow_cal=tomorrow_cal,
        people_report=results["people"],
        project_report=project_report,
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
    elif "--project-status" in sys.argv:
        print("=== PROJECT STATUS AGENT ===")
        print(project_status_agent(triage))
    elif "--project-history" in sys.argv:
        print("=== PROJECT HISTORY AGENT ===")
        print(project_history_agent(triage))
    elif "--project-context" in sys.argv:
        print("=== PROJECT CONTEXT AGENT ===")
        print(project_context_agent(triage))
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
        print("Usage: python agents.py [--people|--project-status|--project-history|--project-context|--calendar|--compose]")
