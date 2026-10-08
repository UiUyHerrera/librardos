import re
from datetime import time

from flask_babel import gettext as _

RANGE_PATTERN = re.compile(r"(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})")
STEP_MINUTES = 30


def parse_ranges(text):
    ranges = []
    for part in (piece.strip() for piece in (text or "").split(",")):
        if not part:
            continue
        match = RANGE_PATTERN.fullmatch(part)
        if match is None:
            raise ValueError(_("Write hours like 09:00-13:00, 15:00-19:00."))
        opens = to_time(match.group(1), match.group(2))
        closes = to_time(match.group(3), match.group(4))
        if opens >= closes:
            raise ValueError(_("Closing time must be after opening time."))
        ranges.append((opens, closes))

    ranges.sort()
    for (_first_opens, first_closes), (second_opens, _second_closes) in zip(ranges, ranges[1:]):
        if second_opens < first_closes:
            raise ValueError(_("Opening hours on the same day cannot overlap."))
    return ranges


def to_time(hours, minutes):
    hours, minutes = int(hours), int(minutes)
    if hours > 23 or minutes not in range(0, 60, STEP_MINUTES):
        raise ValueError(_("Use times on the hour or half hour, up to 23:30."))
    return time(hours, minutes)


def format_ranges(ranges):
    return ", ".join(f"{opens:%H:%M}-{closes:%H:%M}" for opens, closes in ranges)
