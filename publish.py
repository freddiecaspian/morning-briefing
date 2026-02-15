"""Publish episodes and feed to GitHub Pages via git."""

import subprocess
import os

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))


def publish(episode_path, commit_message=None):
    """Stage the new episode and updated feed, commit, and push.

    Args:
        episode_path: Path to the new MP3 file.
        commit_message: Optional custom commit message.
    """
    if commit_message is None:
        filename = os.path.basename(episode_path)
        commit_message = f"Add episode: {filename}"

    def git(*args):
        result = subprocess.run(
            ["git"] + list(args),
            cwd=PROJECT_DIR,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr}")
        return result.stdout.strip()

    # Stage the episode and feed
    git("add", episode_path)
    git("add", "feed.xml")
    git("commit", "-m", commit_message)
    git("push")

    print(f"Published: {commit_message}")


def init_repo(remote_url=None):
    """Initialise the git repo if not already done."""
    git_dir = os.path.join(PROJECT_DIR, ".git")
    if os.path.isdir(git_dir):
        print("Git repo already exists.")
        return

    def git(*args):
        subprocess.run(["git"] + list(args), cwd=PROJECT_DIR, check=True)

    git("init")
    git("add", ".")
    git("commit", "-m", "Initial commit")

    if remote_url:
        git("remote", "add", "origin", remote_url)
        git("push", "-u", "origin", "main")
        print(f"Repo pushed to {remote_url}")


if __name__ == "__main__":
    print("Use init_repo() to set up, or publish() after generating an episode.")
