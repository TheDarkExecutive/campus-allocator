from __future__ import annotations

from typing import List, Tuple, Dict, Optional
from .models import Room, RoomRequest
from .occupancy import OccupancyIndex


class FeasibilityFilter:
    """
    Evaluates hard feasibility constraints:
    1. capacity >= expected_attendance + extra_chairs + 3 * extra_tables
    2. projector present if projector_required
    3. computers present if computers_required
    4. accessible if room has it and request needs it
    5. no hour in the requested slot is occupied
    """

    @staticmethod
    def evaluate(
        room: Room,
        request: RoomRequest,
        occupancy: OccupancyIndex,
        target_date: Optional[str] = None,
        target_hour: Optional[int] = None,
    ) -> Tuple[bool, List[str], List[str]]:
        """
        Evaluates feasibility of a specific room for a request.
        Returns:
            (is_feasible, reason_codes, trace_notes)
        """
        date_str = target_date or request.date
        start_hour = target_hour if target_hour is not None else request.start_hour
        duration = request.duration_hours
        space_needed = request.space_needed

        reasons: List[str] = []
        trace: List[str] = []

        # 1. Capacity check
        if room.capacity < space_needed:
            reasons.append("CAPACITY_DEFICIT")
            trace.append(f"Capacity failure: room holds {room.capacity}, needed {space_needed} ({request.expected_attendance} att + {request.extra_chairs} ch + {request.extra_tables}*3 tbl)")
            return False, reasons, trace

        spare = room.capacity - space_needed
        trace.append(f"Capacity pass: {room.capacity} >= {space_needed} ({spare} spare seats)")

        # 2. Projector check
        if request.projector_required and not room.projector:
            reasons.append("NO_PROJECTOR")
            trace.append("Projector failure: room lacks requested projector")
            return False, reasons, trace
        elif request.projector_required:
            trace.append("Projector pass: projector present")

        # 3. Computers check
        if request.computers_required and not room.computers:
            reasons.append("NO_COMPUTERS")
            trace.append("Computers failure: room lacks requested lab computers")
            return False, reasons, trace
        elif request.computers_required:
            trace.append("Computers pass: lab computers present")

        # 4. Accessibility check
        if request.accessible_required and not room.accessible:
            reasons.append("NOT_ACCESSIBLE")
            trace.append("Accessibility failure: room is not wheelchair accessible")
            return False, reasons, trace
        elif request.accessible_required:
            trace.append("Accessibility pass: wheelchair accessible")

        # 5. Occupancy check
        if not occupancy.is_slot_free(room.room_id, date_str, start_hour, duration):
            clashes = occupancy.get_clashes(room.room_id, date_str, start_hour, duration)
            reasons.append("SCHEDULE_CLASH")
            clash_refs = [f"{c.source_type}:{c.reference_id}@H{c.hour}" for c in clashes]
            trace.append(f"Schedule clash: busy during requested slot [{start_hour}:00-{(start_hour+duration)}:00] ({', '.join(clash_refs)})")
            return False, reasons, trace

        trace.append(f"Schedule pass: slot free on {date_str} [{start_hour}:00-{(start_hour+duration)}:00]")
        reasons.append("FEASIBLE")
        return True, reasons, trace

    @staticmethod
    def find_feasible_rooms(
        rooms: Dict[str, Room],
        request: RoomRequest,
        occupancy: OccupancyIndex,
        target_date: Optional[str] = None,
        target_hour: Optional[int] = None,
    ) -> List[Tuple[Room, List[str]]]:
        """
        Finds all feasible rooms for the given request slot.
        Returns list of (Room, trace_notes).
        """
        feasible: List[Tuple[Room, List[str]]] = []
        for r in rooms.values():
            ok, _, trace = FeasibilityFilter.evaluate(r, request, occupancy, target_date, target_hour)
            if ok:
                feasible.append((r, trace))
        return feasible
