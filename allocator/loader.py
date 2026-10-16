from __future__ import annotations

import csv
import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from dateutil import parser as dt_parser

from .models import Room, ClassSchedule, Event, RoomPreference, RoomRequest


class DataLoader:
    def __init__(self, data_dir: str = "data") -> None:
        self.data_dir = Path(data_dir)

    def load_rooms(self, filename: str = "rooms.csv") -> Dict[str, Room]:
        path = self.data_dir / filename
        rooms: Dict[str, Room] = {}
        if not path.exists():
            return rooms

        try:
            with open(path, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    room_id = row.get("room_id", "").strip()
                    if not room_id:
                        continue
                    room = Room(
                        room_id=room_id,
                        building=row.get("building", "").strip(),
                        floor=int(row.get("floor", "1")),
                        room_type=row.get("room_type", "Classroom").strip(),
                        capacity=int(row.get("capacity", "0")),
                        projector=str(row.get("projector", "")).strip().lower() in ("true", "1", "yes"),
                        computers=str(row.get("computers", "")).strip().lower() in ("true", "1", "yes"),
                        accessible=str(row.get("accessible", "")).strip().lower() in ("true", "1", "yes"),
                        power_outlets=int(row.get("power_outlets", "0")),
                    )
                    rooms[room_id] = room
        except Exception as e:
            # Return whatever was loaded before error
            pass
        return rooms

    def save_rooms(self, rooms: Dict[str, Room], filename: str = "rooms.csv") -> bool:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        path = self.data_dir / filename
        try:
            with open(path, mode="w", encoding="utf-8", newline="") as f:
                fieldnames = [
                    "room_id",
                    "building",
                    "floor",
                    "room_type",
                    "capacity",
                    "projector",
                    "computers",
                    "accessible",
                    "power_outlets",
                ]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for r in rooms.values():
                    writer.writerow(r.to_dict())
            return True
        except Exception:
            return False

    def load_class_schedule(self, filename: str = "class_schedule.csv") -> List[ClassSchedule]:
        path = self.data_dir / filename
        schedules: List[ClassSchedule] = []
        if not path.exists():
            return schedules

        try:
            with open(path, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    sid = row.get("schedule_id", "").strip()
                    rid = row.get("room_id", "").strip()
                    if not sid or not rid:
                        continue
                    schedules.append(
                        ClassSchedule(
                            schedule_id=sid,
                            room_id=rid,
                            course_code=row.get("course_code", "").strip(),
                            weekday=row.get("weekday", "Mon").strip().capitalize()[:3],
                            start_hour=int(row.get("start_hour", "8")),
                            duration_hours=int(row.get("duration_hours", "1")),
                            expected_attendance=int(row.get("expected_attendance", "0")),
                            department=row.get("department", "").strip(),
                        )
                    )
        except Exception:
            pass
        return schedules

    def load_events(self, filename: str = "events.csv") -> List[Event]:
        path = self.data_dir / filename
        events: List[Event] = []
        if not path.exists():
            return events

        try:
            with open(path, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    eid = row.get("event_id", "").strip()
                    rid = row.get("room_id", "").strip()
                    raw_time = row.get("start_time", "").strip()
                    if not eid or not rid or not raw_time:
                        continue
                    try:
                        parsed_dt = dt_parser.parse(raw_time)
                    except Exception:
                        continue

                    actual = row.get("actual_attendance")
                    actual_att = int(actual) if actual and actual.strip().isdigit() else None

                    events.append(
                        Event(
                            event_id=eid,
                            room_id=rid,
                            event_type=row.get("event_type", "Event").strip(),
                            start_time=parsed_dt,
                            duration_hours=int(row.get("duration_hours", "1")),
                            expected_attendance=int(row.get("expected_attendance", "0")),
                            actual_attendance=actual_att,
                        )
                    )
        except Exception:
            pass
        return events

    def load_room_requests_csv(self, filename: str = "room_requests.csv") -> List[RoomRequest]:
        """Loads historical room_requests.csv used strictly for replay validation."""
        path = self.data_dir / filename
        requests: List[RoomRequest] = []
        if not path.exists():
            return requests

        try:
            with open(path, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    req_id = row.get("request_id", "").strip()
                    req_date = row.get("request_date", "").strip()
                    if not req_id or not req_date:
                        continue
                    status = row.get("status", "Approved").strip()
                    requests.append(
                        RoomRequest(
                            request_id=req_id,
                            week=req_date,
                            club=f"Historical-{req_id}",
                            purpose=row.get("purpose", "Club meeting").strip(),
                            date=req_date,
                            start_hour=int(row.get("start_hour", "10")),
                            duration_hours=int(row.get("duration_hours", "2")),
                            expected_attendance=int(row.get("required_capacity", "30")),
                            projector_required=str(row.get("projector_required", "")).strip().lower() in ("true", "1", "yes"),
                            computers_required=str(row.get("computers_required", "")).strip().lower() in ("true", "1", "yes"),
                            extra_chairs=0,
                            extra_tables=0,
                            accessible_required=False,
                            preferences=[],
                            submitted_at=datetime.utcnow(),
                            status=status,
                        )
                    )
        except Exception:
            pass
        return requests

    def load_inbox_week(self, week_str: str, inbox_base: str = "inbox") -> Tuple[List[RoomRequest], List[str]]:
        """Loads all .json files in inbox/<week_str>/."""
        inbox_dir = Path(inbox_base) / week_str
        requests: List[RoomRequest] = []
        errors: List[str] = []

        if not inbox_dir.exists():
            return requests, [f"Inbox directory '{inbox_dir}' does not exist."]

        for filepath in sorted(inbox_dir.glob("*.json")):
            try:
                with open(filepath, mode="r", encoding="utf-8") as f:
                    data = json.load(f)

                prefs: List[RoomPreference] = []
                for p in data.get("preferences", []):
                    prefs.append(RoomPreference(rank=int(p.get("rank", 1)), room_id=p.get("room_id", "").strip()))
                prefs.sort(key=lambda x: x.rank)

                sub_at_raw = data.get("submitted_at")
                if sub_at_raw:
                    try:
                        sub_dt = dt_parser.parse(sub_at_raw)
                    except Exception:
                        sub_dt = datetime.utcnow()
                else:
                    sub_dt = datetime.utcnow()

                req_id = data.get("request_id") or f"REQ-{data.get('club', 'CLUB')[:4].upper()}-{filepath.stem}"

                req = RoomRequest(
                    request_id=req_id,
                    week=data.get("week", week_str),
                    club=data.get("club", "Unknown Club").strip(),
                    purpose=data.get("purpose", "Club meeting").strip(),
                    date=data.get("date", week_str).strip(),
                    start_hour=int(data.get("start_hour", 12)),
                    duration_hours=int(data.get("duration_hours", 2)),
                    expected_attendance=int(data.get("expected_attendance", 20)),
                    projector_required=bool(data.get("projector_required", False)),
                    computers_required=bool(data.get("computers_required", False)),
                    extra_chairs=int(data.get("extra_chairs", 0)),
                    extra_tables=int(data.get("extra_tables", 0)),
                    accessible_required=bool(data.get("accessible_required", False)),
                    preferences=prefs,
                    submitted_at=sub_dt,
                    notes=data.get("notes", ""),
                )
                requests.append(req)
            except Exception as e:
                errors.append(f"Failed parsing '{filepath.name}': {str(e)}")

        return requests, errors

    def write_deferred(self, week_str: str, request: RoomRequest, deferred_base: str = "deferred") -> Path:
        out_dir = Path(deferred_base) / week_str
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{request.request_id}.json"

        data = {
            "request_id": request.request_id,
            "week": request.week,
            "club": request.club,
            "purpose": request.purpose,
            "date": request.date,
            "start_hour": request.start_hour,
            "duration_hours": request.duration_hours,
            "expected_attendance": request.expected_attendance,
            "projector_required": request.projector_required,
            "computers_required": request.computers_required,
            "extra_chairs": request.extra_chairs,
            "extra_tables": request.extra_tables,
            "accessible_required": request.accessible_required,
            "preferences": [{"rank": p.rank, "room_id": p.room_id} for p in request.preferences],
            "submitted_at": request.submitted_at.isoformat(),
            "notes": request.notes,
            "deferred_reason": "Club weekly active limit reached (rolled forward)",
        }
        with open(out_path, mode="w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        return out_path
