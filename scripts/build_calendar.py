#!/usr/bin/env python3
"""Build a standards-compliant ABL iCalendar feed from events.csv."""
from __future__ import annotations

import csv
import os
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(os.environ.get("ABL_EVENTS_CSV", ROOT / "events.csv"))
OUTPUT = Path(os.environ.get("ABL_ICS_OUTPUT", ROOT / "site" / "abl-events.ics"))
DEFAULT_TZ = os.environ.get("ABL_DEFAULT_TIMEZONE", "America/Los_Angeles")
VALID_STATUS = {"CONFIRMED", "TENTATIVE", "CANCELLED"}

def ics_escape(value: str) -> str:
    return (value.replace("\\", "\\\\").replace("\r\n", "\\n")
                 .replace("\n", "\\n").replace("\r", "\\n")
                 .replace(";", "\\;").replace(",", "\\,"))

def fold_line(line: str) -> str:
    """Fold content lines at 75 UTF-8 octets, as required by RFC 5545."""
    chunks, current, count = [], [], 0
    for char in line:
        encoded = char.encode("utf-8")
        if count + len(encoded) > 75:
            chunks.append("".join(current))
            current, count = [" "], 1
        current.append(char)
        count += len(encoded)
    chunks.append("".join(current))
    return "\r\n".join(chunks)

def parse_bool(value: str, rownum: int) -> bool:
    normalized = value.strip().lower()
    if normalized in {"true", "yes", "1"}:
        return True
    if normalized in {"false", "no", "0", ""}:
        return False
    raise ValueError(f"Row {rownum}: all_day must be TRUE or FALSE")

def parse_event_time(value: str, tz_name: str, all_day: bool, rownum: int, field: str):
    value = value.strip()
    if not value:
        raise ValueError(f"Row {rownum}: {field} is required")
    if all_day:
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(f"Row {rownum}: {field} must be YYYY-MM-DD for all-day events") from exc
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"Row {rownum}: invalid {field} datetime {value!r}") from exc
    if dt.tzinfo is None:
        try:
            dt = dt.replace(tzinfo=ZoneInfo(tz_name))
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"Row {rownum}: unknown timezone {tz_name!r}") from exc
    return dt.astimezone(timezone.utc)

def format_dt(value, all_day: bool) -> str:
    return value.strftime("%Y%m%d") if all_day else value.strftime("%Y%m%dT%H%M%SZ")

def load_events():
    if not SOURCE.exists():
        raise FileNotFoundError(f"CSV source not found: {SOURCE}")
    events, seen = [], set()
    with SOURCE.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        required = {"id", "title", "description", "start", "end", "all_day",
                    "timezone", "location", "category", "status"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError("CSV is missing required columns: " + ", ".join(sorted(missing)))
        for rownum, row in enumerate(reader, start=2):
            if not any((v or "").strip() for v in row.values()):
                continue
            event_id = (row.get("id") or "").strip()
            title = (row.get("title") or "").strip()
            if not event_id or not title:
                raise ValueError(f"Row {rownum}: id and title are required")
            if not re.fullmatch(r"[A-Za-z0-9._-]+", event_id):
                raise ValueError(f"Row {rownum}: id may contain only letters, numbers, dot, underscore, hyphen")
            if event_id in seen:
                raise ValueError(f"Row {rownum}: duplicate id {event_id!r}")
            seen.add(event_id)
            all_day = parse_bool(row.get("all_day", ""), rownum)
            tz_name = (row.get("timezone") or "").strip() or DEFAULT_TZ
            start = parse_event_time(row.get("start", ""), tz_name, all_day, rownum, "start")
            end = parse_event_time(row.get("end", ""), tz_name, all_day, rownum, "end")
            if end <= start:
                raise ValueError(f"Row {rownum}: end must be after start")
            status = (row.get("status") or "CONFIRMED").strip().upper()
            if status not in VALID_STATUS:
                raise ValueError(f"Row {rownum}: status must be one of {', '.join(sorted(VALID_STATUS))}")
            events.append({
                "id": event_id, "title": title,
                "description": (row.get("description") or "").strip(),
                "start": start, "end": end, "all_day": all_day,
                "location": (row.get("location") or "").strip(),
                "category": (row.get("category") or "").strip(),
                "status": status,
            })
    return events

def build():
    events = load_events()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//ABL//League Events//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:ABL League Events",
        "X-WR-CALDESC:Meetings, drafts, deadlines, and other ABL league events",
    ]
    for event in events:
        lines.extend([
            "BEGIN:VEVENT",
            f"UID:{event['id']}@abl-league-calendar",
            f"DTSTAMP:{stamp}",
            f"DTSTART{';VALUE=DATE' if event['all_day'] else ''}:{format_dt(event['start'], event['all_day'])}",
            f"DTEND{';VALUE=DATE' if event['all_day'] else ''}:{format_dt(event['end'], event['all_day'])}",
            f"SUMMARY:{ics_escape(event['title'])}",
            f"STATUS:{event['status']}",
            "SEQUENCE:0",
        ])
        if event["description"]:
            lines.append(f"DESCRIPTION:{ics_escape(event['description'])}")
        if event["location"]:
            lines.append(f"LOCATION:{ics_escape(event['location'])}")
        if event["category"]:
            lines.append(f"CATEGORIES:{ics_escape(event['category'])}")
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_bytes(("".join(fold_line(line) + "\r\n" for line in lines)).encode("utf-8"))
    print(f"Wrote {OUTPUT} with {len(events)} event(s)")

if __name__ == "__main__":
    try:
        build()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
