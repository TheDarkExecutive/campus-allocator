from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import List, Optional, Dict, Any


@dataclass
class Room:
    room_id: str
    building: str
    floor: int
    room_type: str
    capacity: int
    projector: bool
    computers: bool
    accessible: bool
    power_outlets: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "room_id": self.room_id,
            "building": self.building,
            "floor": self.floor,
            "room_type": self.room_type,
            "capacity": self.capacity,
            "projector": self.projector,
            "computers": self.computers,
            "accessible": self.accessible,
            "power_outlets": self.power_outlets,
        }


@dataclass
class ClassSchedule:
    schedule_id: str
    room_id: str
    course_code: str
    weekday: str  # Mon, Tue, Wed, Thu, Fri, Sat
    start_hour: int
    duration_hours: int
    expected_attendance: int
    department: str


@dataclass
class Event:
    event_id: str
    room_id: str
    event_type: str
    start_time: datetime
    duration_hours: int
    expected_attendance: int
    actual_attendance: Optional[int] = None


@dataclass
class RoomPreference:
    rank: int
    room_id: str


@dataclass
class RoomRequest:
    request_id: str
    week: str  # e.g. "2025-08-03" (Monday or reference week)
    club: str
    purpose: str
    date: str  # e.g. "2025-08-05"
    start_hour: int
    duration_hours: int
    expected_attendance: int
    projector_required: bool
    computers_required: bool
    extra_chairs: int = 0
    extra_tables: int = 0
    accessible_required: bool = False
    preferences: List[RoomPreference] = field(default_factory=list)
    submitted_at: datetime = field(default_factory=datetime.utcnow)
    notes: str = ""
    status: Optional[str] = None  # Used for replay validation comparisons

    @property
    def space_needed(self) -> int:
        return self.expected_attendance + self.extra_chairs + (3 * self.extra_tables)


@dataclass
class OccupancySlot:
    room_id: str
    date: str  # YYYY-MM-DD
    hour: int  # 0..23
    source_type: str  # "class" | "event" | "allocated"
    reference_id: str


@dataclass
class Decision:
    request_id: str
    club: str
    final_status: str  # "Approved" | "Moved" | "Waitlisted" | "Rejected" | "Deferred"
    assigned_room: Optional[str] = None
    assigned_date: Optional[str] = None
    assigned_hour: Optional[int] = None
    reason_codes: List[str] = field(default_factory=list)
    rule_trace: List[str] = field(default_factory=list)
    decided_by: str = "kernel"  # "kernel" | "admin" | "llm-flag"
    why: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "club": self.club,
            "final_status": self.final_status,
            "assigned_room": self.assigned_room,
            "assigned_date": self.assigned_date,
            "assigned_hour": self.assigned_hour,
            "reason_codes": self.reason_codes,
            "rule_trace": self.rule_trace,
            "decided_by": self.decided_by,
            "why": self.why,
        }


@dataclass
class AdminOverride:
    timestamp: str
    request_id: str
    admin_action: str
    original_decision: Dict[str, Any]
    new_decision: Dict[str, Any]
    notes: str = ""


@dataclass
class ExceptionCase:
    exception_id: str
    request: RoomRequest
    exception_type: str  # "CONTESTED_SLOT" | "NO_FEASIBLE_ROOM" | "TIGHT_FIT" | "SAME_TIMESTAMP_TIE" | "CLUB_CAP_CONFLICT" | "LATE_SUBMISSION" | "STALE_DATA" | "MANUAL_FLAG"
    situation: str
    auto_pick: Optional[str] = None
    possible_rooms: List[str] = field(default_factory=list)
    candidate_requests: List[RoomRequest] = field(default_factory=list)
    resolved: bool = False
    chosen_action: Optional[str] = None


@dataclass
class AllocationResult:
    week: str
    decisions: List[Decision]
    exceptions: List[ExceptionCase]
    overrides: List[AdminOverride] = field(default_factory=list)
    flags: List[str] = field(default_factory=list)


@dataclass
class Settings:
    shared_folder: str = "reports"
    week_start_day: str = "Monday"
    enable_llm: bool = True
    llm_model: str = "gemma2:2b"
    ollama_url: str = "http://localhost:11434"
