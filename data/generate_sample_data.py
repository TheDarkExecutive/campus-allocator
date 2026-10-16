"""
Generates production baseline datasets conforming to the specification:
- data/rooms.csv (120 rooms across 5 buildings)
- data/class_schedule.csv (5,000 class slots)
- data/events.csv (1,800 campus events)
- data/room_requests.csv (5,000 historical labeled requests)
- inbox/2025-08-03/*.json (sample club submissions)
"""

import csv
import json
import random
from datetime import datetime, timedelta
from pathlib import Path

random.seed(42)

DATA_DIR = Path(__file__).parent
DATA_DIR.mkdir(parents=True, exist_ok=True)

BUILDINGS = ["North", "South", "Central", "East", "West"]
ROOM_TYPES = ["Classroom", "Lecture Hall", "Seminar Room", "Computer Lab"]
DEPTS = ["CS", "ECE", "MECH", "MATH", "PHYS", "CHEM", "MGMT", "HUM"]
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]


def generate_rooms():
    path = DATA_DIR / "rooms.csv"
    if path.exists():
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["room_id", "building", "floor", "room_type", "capacity", "projector", "computers", "accessible", "power_outlets"])
        for i in range(1, 121):
            rid = f"R{i:03d}"
            b = BUILDINGS[(i - 1) % len(BUILDINGS)]
            floor = ((i - 1) // 25) % 4 + 1
            rtype = ROOM_TYPES[(i - 1) % len(ROOM_TYPES)]
            cap = random.choice([25, 35, 45, 60, 80, 120, 160, 200])
            proj = random.random() < 0.85
            comp = rtype == "Computer Lab" or random.random() < 0.25
            acc = random.random() < 0.90
            outlets = random.choice([8, 12, 16, 24, 32])
            writer.writerow([rid, b, floor, rtype, cap, proj, comp, acc, outlets])


def generate_class_schedules():
    path = DATA_DIR / "class_schedule.csv"
    if path.exists():
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["schedule_id", "room_id", "course_code", "weekday", "start_hour", "duration_hours", "expected_attendance", "department"])
        for i in range(1, 5001):
            sid = f"SCH-{i:05d}"
            rid = f"R{random.randint(1, 120):03d}"
            dept = random.choice(DEPTS)
            code = f"{dept}{random.randint(100, 499)}"
            w = random.choice(WEEKDAYS)
            start_h = random.choice([8, 9, 10, 11, 13, 14, 15, 16, 17])
            dur = random.choice([1, 2])
            att = random.randint(20, 75)
            writer.writerow([sid, rid, code, w, start_h, dur, att, dept])


def generate_events():
    path = DATA_DIR / "events.csv"
    if path.exists():
        return
    base_date = datetime(2025, 8, 4, 8, 0, 0)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["event_id", "room_id", "event_type", "start_time", "duration_hours", "expected_attendance", "actual_attendance"])
        for i in range(1, 1801):
            eid = f"EVT-{i:04d}"
            rid = f"R{random.randint(1, 120):03d}"
            etype = random.choice(["Guest Lecture", "Department Meeting", "Seminar", "Workshop", "Conference"])
            day_offset = random.randint(0, 6)
            start_h = random.choice([9, 11, 14, 16, 18])
            dt = base_date + timedelta(days=day_offset, hours=(start_h - 8))
            dur = random.choice([1, 2, 3])
            exp = random.randint(30, 150)
            act = exp + random.randint(-5, 10)
            writer.writerow([eid, rid, etype, dt.strftime("%Y-%m-%d %H:%M:%S"), dur, exp, act])


def generate_room_requests():
    path = DATA_DIR / "room_requests.csv"
    if path.exists():
        return
    base_date = datetime(2025, 8, 4)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["request_id", "request_date", "start_hour", "duration_hours", "required_capacity", "projector_required", "computers_required", "purpose", "status"])
        for i in range(1, 5001):
            req_id = f"HIST-{i:05d}"
            dt = (base_date + timedelta(days=random.randint(0, 13))).strftime("%Y-%m-%d")
            sh = random.choice([9, 10, 11, 13, 14, 15, 16, 17])
            dur = random.choice([1, 2])
            req_cap = random.choice([25, 35, 45, 60, 80, 110])
            proj = random.random() < 0.70
            comp = random.random() < 0.20
            purpose = random.choice(["Club meeting", "Guest lecture", "Study group", "Workshop", "Review session"])
            status = random.choices(["Approved", "Rejected", "Waitlisted"], weights=[0.72, 0.20, 0.08])[0]
            writer.writerow([req_id, dt, sh, dur, req_cap, proj, comp, purpose, status])


def generate_inbox_samples():
    inbox_dir = DATA_DIR.parent / "inbox" / "2025-08-03"
    inbox_dir.mkdir(parents=True, exist_ok=True)

    samples = [
        {
            "week": "2025-08-03",
            "club": "Robotics Club",
            "purpose": "Annual Hackathon Workshop",
            "date": "2025-08-05",
            "start_hour": 13,
            "duration_hours": 2,
            "expected_attendance": 40,
            "projector_required": True,
            "computers_required": False,
            "extra_chairs": 6,
            "extra_tables": 2,
            "preferences": [{"rank": 1, "room_id": "R063"}, {"rank": 2, "room_id": "R101"}, {"rank": 3, "room_id": "R024"}],
            "submitted_at": "2025-08-01T14:22:00Z",
            "notes": "Need front podium space for demo robot"
        },
        {
            "week": "2025-08-03",
            "club": "Debate Society",
            "purpose": "Inter-University Parliamentary Debate",
            "date": "2025-08-05",
            "start_hour": 14,
            "duration_hours": 2,
            "expected_attendance": 50,
            "projector_required": True,
            "computers_required": False,
            "extra_chairs": 10,
            "extra_tables": 3,
            "preferences": [{"rank": 1, "room_id": "R101"}, {"rank": 2, "room_id": "R063"}],
            "submitted_at": "2025-08-01T15:10:00Z",
            "notes": "Audience seating required"
        },
        {
            "week": "2025-08-03",
            "club": "AI & ML Society",
            "purpose": "Deep Learning GPU Tutorial",
            "date": "2025-08-05",
            "start_hour": 13,
            "duration_hours": 2,
            "expected_attendance": 35,
            "projector_required": True,
            "computers_required": True,
            "extra_chairs": 0,
            "extra_tables": 0,
            "preferences": [{"rank": 1, "room_id": "R004"}, {"rank": 2, "room_id": "R008"}],
            "submitted_at": "2025-08-01T16:00:00Z",
            "notes": "Require lab workstation computers"
        },
        {
            "week": "2025-08-03",
            "club": "Robotics Club",
            "purpose": "Secondary Executive Committee Sync",
            "date": "2025-08-06",
            "start_hour": 17,
            "duration_hours": 1,
            "expected_attendance": 12,
            "projector_required": False,
            "computers_required": False,
            "extra_chairs": 0,
            "extra_tables": 0,
            "preferences": [{"rank": 1, "room_id": "R020"}],
            "submitted_at": "2025-08-02T10:00:00Z",
            "notes": "Second request in same week; subject to club quota"
        }
    ]

    for s in samples:
        filename = f"{s['club'].lower().replace(' ', '_')}_{s['date']}.json"
        with open(inbox_dir / filename, "w", encoding="utf-8") as f:
            json.dump(s, f, indent=2)


if __name__ == "__main__":
    generate_rooms()
    generate_class_schedules()
    generate_events()
    generate_room_requests()
    generate_inbox_samples()
    print("Baseline datasets successfully generated.")
