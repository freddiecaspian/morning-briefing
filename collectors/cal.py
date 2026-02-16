"""Pull today's and tomorrow's calendar events via Google Calendar ICS feed.

Fetches the ICS feed over HTTP, parses with icalendar + recurring_ical_events,
filters to the target date range. No AppleScript, no Calendar.app dependency.

Replaces the old AppleScript approach (saved as calendar_applescript_v2.py).
"""

import os
import requests
from datetime import datetime, timedelta, date
from icalendar import Calendar
from recurring_ical_events import of as events_of
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# Comma-separated ICS feed URLs from .env
ICS_URLS_RAW = os.getenv("GOOGLE_CALENDAR_ICS_URLS", "")


def _fetch_ics(url, timeout=30):
    """Fetch an ICS feed and return parsed Calendar object."""
    resp = requests.get(url.strip(), timeout=timeout)
    resp.raise_for_status()
    return Calendar.from_ical(resp.content)


def _event_to_dict(component):
    """Convert an icalendar VEVENT component to our standard event dict."""
    title = str(component.get("SUMMARY", "Untitled"))
    if len(title) > 200:
        title = title[:100] + "..."

    dtstart = component.get("DTSTART").dt
    dtend = component.get("DTEND")
    if dtend:
        dtend = dtend.dt
    else:
        dtend = dtstart + timedelta(hours=1)

    location = str(component.get("LOCATION", "")) or ""

    # All-day events have date objects, timed events have datetime objects
    is_all_day = isinstance(dtstart, date) and not isinstance(dtstart, datetime)

    if is_all_day:
        return {
            "title": title,
            "start": "00:00",
            "end": "23:59",
            "duration_mins": 1440,
            "is_all_day": True,
            "location": location,
        }

    # Timed event - convert to local time if timezone-aware
    if hasattr(dtstart, 'astimezone'):
        dtstart = dtstart.astimezone()
    if hasattr(dtend, 'astimezone'):
        dtend = dtend.astimezone()

    duration_mins = int((dtend - dtstart).total_seconds() / 60)

    return {
        "title": title,
        "start": dtstart.strftime("%H:%M"),
        "end": dtend.strftime("%H:%M"),
        "duration_mins": duration_mins,
        "is_all_day": False,
        "location": location,
    }


def get_events(day_offset=0, min_duration_mins=15):
    """Get calendar events for a given day across all ICS feeds.

    Returns same format as before:
    [{"title", "start", "end", "duration_mins", "is_all_day", "location"}]
    """
    if not ICS_URLS_RAW:
        print("No GOOGLE_CALENDAR_ICS_URLS set in .env")
        return []

    urls = [u.strip() for u in ICS_URLS_RAW.split(",") if u.strip()]
    target_date = (datetime.now() + timedelta(days=day_offset)).date()
    start = datetime(target_date.year, target_date.month, target_date.day)
    end = start + timedelta(days=1)

    all_events = []

    for url in urls:
        try:
            cal = _fetch_ics(url)
            day_events = events_of(cal).between(start, end)
            for component in day_events:
                event = _event_to_dict(component)
                if not event["is_all_day"] and event["duration_mins"] < min_duration_mins:
                    continue
                all_events.append(event)
        except Exception as e:
            short = url.split("/")[-2][:20] if "/" in url else url[:30]
            print(f"Calendar feed error ({short}): {e}")

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
