"""Generate and update a podcast RSS feed."""

import os
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import formatdate
from time import mktime

FEED_PATH = os.path.join(os.path.dirname(__file__), "feed.xml")

# Update these once the GitHub Pages URL is set
BASE_URL = "https://freddiecaspian.github.io/morning-briefing"

PODCAST_TITLE = "Morning Briefing"
PODCAST_DESCRIPTION = "Your personal daily briefing - tasks, calendar, and priorities."
PODCAST_AUTHOR = "Freddie"
PODCAST_LANGUAGE = "en"


def create_or_update_feed(episode_filename, episode_title, episode_description, episode_date=None, file_size_bytes=0):
    """Add a new episode to the RSS feed.

    Args:
        episode_filename: MP3 filename (e.g. "2026-02-15.mp3")
        episode_title: Episode title
        episode_description: Episode summary text
        episode_date: datetime object (defaults to now)
        file_size_bytes: Size of the MP3 file in bytes
    """
    if episode_date is None:
        episode_date = datetime.now()

    if os.path.exists(FEED_PATH):
        tree = ET.parse(FEED_PATH)
        root = tree.getroot()
        channel = root.find("channel")
    else:
        root = ET.Element("rss")
        root.set("version", "2.0")
        root.set("xmlns:itunes", "http://www.itunes.com/dtds/podcast-1.0.dtd")
        channel = ET.SubElement(root, "channel")
        ET.SubElement(channel, "title").text = PODCAST_TITLE
        ET.SubElement(channel, "description").text = PODCAST_DESCRIPTION
        ET.SubElement(channel, "language").text = PODCAST_LANGUAGE
        ET.SubElement(channel, "link").text = BASE_URL

        # iTunes tags for podcast apps
        ET.SubElement(channel, "{http://www.itunes.com/dtds/podcast-1.0.dtd}author").text = PODCAST_AUTHOR
        ET.SubElement(channel, "{http://www.itunes.com/dtds/podcast-1.0.dtd}summary").text = PODCAST_DESCRIPTION
        ET.SubElement(channel, "{http://www.itunes.com/dtds/podcast-1.0.dtd}explicit").text = "no"

        tree = ET.ElementTree(root)

    # Update lastBuildDate (insert before first <item> so it stays at channel top)
    existing_build = channel.find("lastBuildDate")
    if existing_build is not None:
        channel.remove(existing_build)
    build_date_elem = ET.Element("lastBuildDate")
    build_date_elem.text = formatdate(mktime(episode_date.timetuple()))
    # Find the index of the first <item> and insert before it
    items = list(channel)
    insert_idx = next((i for i, child in enumerate(items) if child.tag == "item"), len(items))
    channel.insert(insert_idx, build_date_elem)

    # Add new episode item
    item = ET.SubElement(channel, "item")
    ET.SubElement(item, "title").text = episode_title
    ET.SubElement(item, "description").text = episode_description

    enclosure = ET.SubElement(item, "enclosure")
    enclosure.set("url", f"{BASE_URL}/episodes/{episode_filename}")
    enclosure.set("type", "audio/mpeg")
    enclosure.set("length", str(file_size_bytes))

    ET.SubElement(item, "pubDate").text = formatdate(mktime(episode_date.timetuple()))

    guid = ET.SubElement(item, "guid")
    guid.text = f"{BASE_URL}/episodes/{episode_filename}"
    guid.set("isPermaLink", "true")

    # Write the feed
    _indent(root)
    tree.write(FEED_PATH, encoding="unicode", xml_declaration=True)
    print(f"Feed updated: {FEED_PATH}")


def _indent(elem, level=0):
    """Add pretty-print indentation to XML."""
    indent = "\n" + "  " * level
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = indent + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = indent
        for child in elem:
            _indent(child, level + 1)
        if not child.tail or not child.tail.strip():
            child.tail = indent
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = indent


if __name__ == "__main__":
    create_or_update_feed(
        "test.mp3",
        "Test Episode - 15 Feb 2026",
        "A test episode to verify the feed works.",
        file_size_bytes=50000,
    )
    print("Feed created. Check feed.xml")
