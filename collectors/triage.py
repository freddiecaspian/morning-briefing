"""Parse a triage note and extract structured data for the briefing."""

import re
import os


def parse_triage(triage_path):
    """Read a triage note and extract key sections for the briefing.

    Returns a dict with:
        - summary: the triage summary text
        - urgent: list of urgent task names
        - active: list of active task names
        - quick_wins: list of quick win task names
        - new_tasks: list of newly surfaced tasks
        - total_count: total items surfaced
        - carried_forward: count of carried-forward items
    """
    with open(triage_path, "r") as f:
        content = f.read()

    result = {
        "summary": "",
        "urgent": [],
        "active": [],
        "keen": [],
        "quick_wins": [],
        "today": [],
        "this_week": [],
        "new_tasks": [],
        "total_count": 0,
        "carried_forward": 0,
        "raw_summary": "",
    }

    # Extract the triage summary section
    summary_match = re.search(
        r"## Triage summary\s*\n(.*?)(?=\n## |\n---|\Z)",
        content,
        re.DOTALL,
    )
    if summary_match:
        result["summary"] = summary_match.group(1).strip()
        result["raw_summary"] = result["summary"]

    # Extract task names from bold markers: **Task name** - description
    def extract_tasks(section_name, content):
        pattern = rf"(?:###?\s*{section_name}.*?\n)(.*?)(?=\n###?\s|\n---|\Z)"
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        if not match:
            return []
        section = match.group(1)
        tasks = re.findall(r"\*\*(.+?)\*\*(?:\s*[-–—]\s*(.+?))?(?:\n|$)", section)
        return [{"name": t[0].strip(), "desc": t[1].strip() if t[1] else ""} for t in tasks]

    result["urgent"] = extract_tasks("Urgent", content)
    result["active"] = extract_tasks("Active", content)
    result["keen"] = extract_tasks("Keen", content)
    result["quick_wins"] = extract_tasks("Quick wins", content)
    result["today"] = extract_tasks("Today", content)
    result["this_week"] = extract_tasks("This week", content)

    # Count totals
    all_tasks = re.findall(r"\*\*(.+?)\*\*", content)
    result["total_count"] = len(all_tasks)

    # Count carried forward
    carry_sections = re.findall(r"carrying forward", content, re.IGNORECASE)
    result["carried_forward"] = len(carry_sections)

    return result


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        data = parse_triage(sys.argv[1])
        print(f"Summary: {data['summary'][:200]}...")
        print(f"Urgent: {len(data['urgent'])} items")
        print(f"Active: {len(data['active'])} items")
        print(f"Quick wins: {len(data['quick_wins'])} items")
        print(f"Total: {data['total_count']} items")
    else:
        print("Usage: python triage.py <path-to-triage-note>")
