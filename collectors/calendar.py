"""Pull today's and tomorrow's calendar events via Calendar.app AppleScript.
Filters out events shorter than 15 minutes.
Uses direct 'whose' query on specific calendar for speed."""

import subprocess
from datetime import datetime, timedelta

# Calendars to include in the briefing
TARGET_CALENDARS = ["freddiecaspian@gmail.com", "Home", "ICloud"]

# AppleScript template - queries one calendar at a time using 'whose' for speed.
# The 'whose' clause on a single named calendar is fast enough even with 7000+ events.
APPLESCRIPT_ONE_CAL = '''
set today to current date
set day of today to TARGET_DAY
set month of today to TARGET_MONTH
set year of today to TARGET_YEAR
set hours of today to 0
set minutes of today to 0
set seconds of today to 0
set tomorrow to today + (1 * days)

tell application "Calendar"
    tell calendar "TARGET_CAL_NAME"
        set todayEvents to (every event whose start date >= today and start date < tomorrow)
    end tell

    set output to ""
    repeat with evt in todayEvents
        set evtTitle to summary of evt
        set s to start date of evt
        set e to end date of evt
        set evtAllDay to allday event of evt
        set durationMins to (((e - s) / 60) as integer)

        set startH to text -2 thru -1 of ("0" & ((hours of s) as text))
        set startM to text -2 thru -1 of ("0" & ((minutes of s) as text))
        set endH to text -2 thru -1 of ("0" & ((hours of e) as text))
        set endM to text -2 thru -1 of ("0" & ((minutes of e) as text))

        set evtLoc to ""
        try
            set evtLoc to location of evt
            if evtLoc is missing value then set evtLoc to ""
        end try

        set output to output & evtTitle & "|||" & startH & ":" & startM & "|||" & endH & ":" & endM & "|||" & durationMins & "|||" & evtAllDay & "|||" & evtLoc & linefeed
    end repeat
    return output
end tell
'''


def _build_script(cal_name, day, month, year):
    """Build AppleScript for one calendar and date."""
    script = APPLESCRIPT_ONE_CAL
    script = script.replace("TARGET_CAL_NAME", cal_name)
    script = script.replace("TARGET_DAY", str(day))
    script = script.replace("TARGET_MONTH", str(month))
    script = script.replace("TARGET_YEAR", str(year))
    return script


def parse_events(raw_output, min_duration_mins=15):
    """Parse AppleScript output into structured events, filtering short ones."""
    events = []
    for line in raw_output.strip().split("\n"):
        if not line.strip() or "|||" not in line:
            continue
        parts = line.split("|||")
        if len(parts) < 5:
            continue

        title = parts[0].strip()
        # Skip events with very long titles (these are notes/descriptions, not real events)
        if len(title) > 200:
            title = title[:100] + "..."

        try:
            start_time = parts[1].strip()
            end_time = parts[2].strip()
            duration_mins = int(parts[3].strip())
            is_all_day = parts[4].strip().lower() == "true"
            location = parts[5].strip() if len(parts) > 5 else ""
        except (ValueError, IndexError):
            continue

        # Filter out events shorter than min_duration_mins (unless all-day)
        if not is_all_day and duration_mins < min_duration_mins:
            continue

        events.append({
            "title": title,
            "start": start_time,
            "end": end_time,
            "duration_mins": duration_mins,
            "is_all_day": is_all_day,
            "location": location,
        })

    # Sort by start time
    events.sort(key=lambda e: e["start"])
    return events


def get_events(day_offset=0, min_duration_mins=15):
    """Get calendar events for a given day across all target calendars."""
    target = datetime.now() + timedelta(days=day_offset)
    all_events = []

    for cal_name in TARGET_CALENDARS:
        script = _build_script(
            cal_name=cal_name,
            day=target.day,
            month=target.month,
            year=target.year,
        )

        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode == 0 and result.stdout.strip():
                all_events.extend(parse_events(result.stdout, min_duration_mins))
            elif result.returncode != 0:
                print(f"Calendar '{cal_name}' error: {result.stderr[:100]}")
        except subprocess.TimeoutExpired:
            print(f"Calendar '{cal_name}' timed out")
        except Exception as e:
            print(f"Calendar '{cal_name}' exception: {e}")

    # Sort combined events by start time
    all_events.sort(key=lambda e: e["start"])
    return all_events


def get_today():
    return get_events(day_offset=0)


def get_tomorrow():
    return get_events(day_offset=1)


if __name__ == "__main__":
    print("Today's events (>= 15 min):")
    today = get_today()
    if not today:
        print("  (none)")
    for e in today:
        allday = " (all day)" if e["is_all_day"] else ""
        loc = f" @ {e['location']}" if e["location"] else ""
        print(f"  {e['start']}-{e['end']} {e['title'][:60]} ({e['duration_mins']}min){allday}{loc}")

    print(f"\nTomorrow's events (>= 15 min):")
    tomorrow = get_tomorrow()
    if not tomorrow:
        print("  (none)")
    for e in tomorrow:
        allday = " (all day)" if e["is_all_day"] else ""
        loc = f" @ {e['location']}" if e["location"] else ""
        print(f"  {e['start']}-{e['end']} {e['title'][:60]} ({e['duration_mins']}min){allday}{loc}")
