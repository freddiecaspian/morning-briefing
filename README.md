# morning-briefing

A nightly podcast that reads me into my own day. It triages the news and my calendar, writes a script with Claude, voices it with ElevenLabs, and publishes to a private RSS feed - so the briefing is waiting by the time I wake up.

## How it works

- **Collect** - pulls the day's news and calendar (`collectors/`, `run_triage.py`)
- **Compose** - Claude turns the raw material into a spoken-word script (`compose.py`, `personality.md`)
- **Voice** - ElevenLabs renders the audio (`audio.py`)
- **Publish** - builds the podcast RSS feed and ships the episode (`feed.py`, `publish.py`)

Runs itself on a nightly schedule. A personal project, not packaged for reuse.
