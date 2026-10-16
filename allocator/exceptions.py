from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from .models import Room, RoomRequest, ExceptionCase, AdminOverride, Decision
from .occupancy import OccupancyIndex
from .feasibility import FeasibilityFilter


class ExceptionDetector:
    """
    Detects ambiguous or edge-case conditions requiring human review:
    - CONTESTED_SLOT: Two requests competing for the exact same room/time
    - NO_FEASIBLE_ROOM: Zero rooms meet the hard constraints
    - TIGHT_FIT: Assigned room has <= 3 spare seats (chair addition risk)
    - SAME_TIMESTAMP_TIE: Identical priority and submission timestamp
    - CLUB_CAP_CONFLICT: Club submitted multiple requests labeled critical/exam
    - LATE_SUBMISSION: Submitted past deadline / cycle cutoff
    - STALE_DATA: Request notes claim room was free, but kernel detects busy
    - MANUAL_FLAG: Notes explicitly request special faculty/admin review
    """

    @staticmethod
    def check_tight_fit(room: Room, request: RoomRequest) -> Optional[ExceptionCase]:
        spare = room.capacity - request.space_needed
        if 0 <= spare <= 3:
            return ExceptionCase(
                exception_id=f"EXC-TIGHT-{uuid.uuid4().hex[:6]}",
                request=request,
                exception_type="TIGHT_FIT",
                situation=f"Room {room.room_id} fits {room.capacity} for needed {request.space_needed} ({spare} spare seats remaining). Furniture addition may be impractical.",
                auto_pick=room.room_id,
                possible_rooms=[room.room_id],
            )
        return None

    @staticmethod
    def check_no_feasible(request: RoomRequest, candidate_rooms: List[str]) -> ExceptionCase:
        return ExceptionCase(
            exception_id=f"EXC-NOFEAS-{uuid.uuid4().hex[:6]}",
            request=request,
            exception_type="NO_FEASIBLE_ROOM",
            situation=f"No feasible room found for {request.club} on {request.date} at hour {request.start_hour} (needed {request.space_needed} space, proj={request.projector_required}, comp={request.computers_required}).",
            auto_pick=None,
            possible_rooms=candidate_rooms[:5],
        )

    @staticmethod
    def check_contested_slot(
        req_a: RoomRequest,
        req_b: RoomRequest,
        room: Room,
        winner_id: Optional[str] = None,
    ) -> ExceptionCase:
        situation = (
            f"Contested Slot in {room.room_id} on {req_a.date} H{req_a.start_hour}: "
            f"'{req_a.club}' ({req_a.purpose}) vs '{req_b.club}' ({req_b.purpose})."
        )
        return ExceptionCase(
            exception_id=f"EXC-CLASH-{uuid.uuid4().hex[:6]}",
            request=req_a,
            exception_type="CONTESTED_SLOT",
            situation=situation,
            auto_pick=winner_id,
            candidate_requests=[req_a, req_b],
            possible_rooms=[room.room_id],
        )

    @staticmethod
    def check_manual_flags(request: RoomRequest) -> Optional[ExceptionCase]:
        notes_lower = request.notes.lower()
        flag_keywords = ["urgent", "escalate", "special permission", "dean", "override", "vip"]
        for kw in flag_keywords:
            if kw in notes_lower:
                return ExceptionCase(
                    exception_id=f"EXC-FLAG-{uuid.uuid4().hex[:6]}",
                    request=request,
                    exception_type="MANUAL_FLAG",
                    situation=f"Club coordinator requested manual review in submission notes: '{request.notes}'",
                    auto_pick=None,
                )
        return None
