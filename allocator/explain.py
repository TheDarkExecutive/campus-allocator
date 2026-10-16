from __future__ import annotations

from typing import List, Optional, Dict, Any
from .models import Room, RoomRequest, Decision
from .occupancy import OccupancyIndex


class ExplanationBuilder:
    """
    Builds clean, deterministic rule traces and human-readable explanations (--why traces).
    """

    @staticmethod
    def build_approval_why(
        room: Room,
        request: RoomRequest,
        occupancy: OccupancyIndex,
        score_breakdown: Optional[Dict[str, Any]] = None,
        alternative_room: Optional[Room] = None,
        is_moved: bool = False,
    ) -> Tuple[str, List[str]]:
        spare = room.capacity - request.space_needed
        trace: List[str] = []

        trace.append(f"Capacity {room.capacity} >= {request.space_needed} ({spare} spare seats)")
        if request.projector_required:
            trace.append("Projector present in room")
        if request.computers_required:
            trace.append("Lab computers available")
        if request.accessible_required:
            trace.append("Wheelchair accessibility verified")

        util = occupancy.get_utilization(room.room_id, request.date)
        trace.append(f"No class or event clash ({room.room_id} on {request.date} H{request.start_hour}-{request.start_hour+request.duration_hours} free)")
        
        if alternative_room is not None:
            alt_util = occupancy.get_utilization(alternative_room.room_id, request.date)
            trace.append(f"Utilization {util:.2f} -> preferred over {alternative_room.room_id} ({alt_util:.2f})")
        else:
            trace.append(f"Room utilization: {util:.2f}")

        if is_moved:
            why_lines = [
                f"Relocated to {room.room_id} due to requested preference clash.",
                f"Why: capacity {room.capacity} >= {request.space_needed} ({spare} spare)",
                f"     {'projector present' if room.projector else 'standard classroom'}",
                f"     no clash on {request.date} hours {request.start_hour}..{request.start_hour+request.duration_hours-1}",
                f"     utilization {util:.2f}",
            ]
        else:
            why_lines = [
                f"Approved for {room.room_id}.",
                f"Why: capacity {room.capacity} >= {request.space_needed} ({spare} spare)",
                f"     {'projector present' if room.projector else 'standard classroom'}",
                f"     no clash on {request.date} hours {request.start_hour}..{request.start_hour+request.duration_hours-1}",
                f"     utilization {util:.2f}",
            ]

        return "\n".join(why_lines), trace

    @staticmethod
    def build_rejection_why(
        request: RoomRequest,
        failure_reasons: List[str],
    ) -> Tuple[str, List[str]]:
        trace = list(failure_reasons)
        lines = [
            f"Rejected: no feasible room found matching constraints on {request.date} at hour {request.start_hour}.",
            f"Why: {'; '.join(failure_reasons)}",
        ]
        return "\n".join(lines), trace

    @staticmethod
    def build_deferred_why(
        request: RoomRequest,
        reason: str,
    ) -> Tuple[str, List[str]]:
        trace = [reason, "Deferred to next cycle without rejection penalty"]
        lines = [
            f"Deferred: {reason}",
            "Why: Club weekly active quota exceeded. Earlier submission preserved.",
            "     Request rolled forward to next allocation run in deferred/ folder.",
        ]
        return "\n".join(lines), trace
