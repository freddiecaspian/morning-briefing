"""Run the /triage skill via Claude Code CLI and return the path to the new triage note."""

import subprocess
import os
import re
from pathlib import Path
from datetime import datetime

VAULT = "/Users/freddiechambers/Library/Mobile Documents/iCloud~md~obsidian/Documents/iCloud"
TRIAGE_DIR = os.path.join(VAULT, "4. Notes", "Morning Triage")


def get_latest_triage_before():
    """Get the set of triage files that exist before running."""
    if not os.path.isdir(TRIAGE_DIR):
        return set()
    return set(os.listdir(TRIAGE_DIR))


def find_new_triage(before_files):
    """Find the new triage file created after running the command."""
    after_files = set(os.listdir(TRIAGE_DIR))
    new_files = after_files - before_files
    if new_files:
        # Return the newest file
        newest = max(new_files, key=lambda f: os.path.getmtime(os.path.join(TRIAGE_DIR, f)))
        return os.path.join(TRIAGE_DIR, newest)
    # If no new file, return the most recently modified file
    all_files = [f for f in os.listdir(TRIAGE_DIR) if f.endswith(".md")]
    if not all_files:
        return None
    newest = max(all_files, key=lambda f: os.path.getmtime(os.path.join(TRIAGE_DIR, f)))
    return os.path.join(TRIAGE_DIR, newest)


def run_triage():
    """Invoke /triage via Claude Code CLI and return the path to the generated note."""
    before = get_latest_triage_before()

    result = subprocess.run(
        [
            "claude",
            "-p",
            "/triage",
            "--dangerously-skip-permissions",
            "--allowedTools", "Bash,Edit,Read,Write,Glob,Grep",
        ],
        cwd=VAULT,
        capture_output=True,
        text=True,
        timeout=300,  # 5 min max
    )

    if result.returncode != 0:
        raise RuntimeError(f"Triage failed: {result.stderr}")

    # Find the new triage note
    triage_path = find_new_triage(before)
    if triage_path:
        print(f"Triage note created: {triage_path}")
        return triage_path
    else:
        raise RuntimeError("Triage ran but no note was found in Morning Triage folder")


if __name__ == "__main__":
    path = run_triage()
    print(f"Triage note: {path}")
