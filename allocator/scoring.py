from __future__ import annotations

from typing import Dict, Optional, Tuple, List
from .models import Room, RoomRequest
from .occupancy import OccupancyIndex


PURPOSE_PRIORITY = {
    "exam": 4,
    "faculty": 3,
    "club": 2,
    "study": 1,
}


def get_purpose_score(purpose: str) -> int:
    """Returns integer rank for purpose (higher is more critical)."""
    p_lower = purpose.lower().strip()
    for key, val in PURPOSE_PRIORITY.items():
        if key in p_lower:
            return val
    return 2  # default to club level


class RoomScorer:
    """
    Computes soft ranking scores for feasible rooms:
    score =
        - 0.45 * (abs(capacity - space_needed) / 200)
        + 0.25 * facility_match_ratio
        + 0.20 * (1 - utilization(room_id, date))
        + 0.10 * preference_bonus(room_id, request)
    """

    @staticmethod
    def preference_bonus(room_id: str, request: RoomRequest) -> float:
        for pref in request.preferences:
            if pref.room_id == room_id:
                if pref.rank == 1:
                    return 1.0
                elif pref.rank == 2:
                    return 0.6
                elif pref.rank == 3:
                    return 0.3
        return 0.0

    @staticmethod
    def facility_match_ratio(room: Room, request: RoomRequest) -> float:
        req_checks = []
        if request.projector_required:
            req_checks.append(1.0 if room.projector else 0.0)
        if request.computers_required:
            req_checks.append(1.0 if room.computers else 0.0)
        if request.accessible_required:
            req_checks.append(1.0 if room.accessible else 0.0)

        base_ratio = sum(req_checks) / len(req_checks) if req_checks else 1.0
        # Power outlet bonus (normalized up to 20 outlets)
        outlet_bonus = min(1.0, room.power_outlets / 20.0) * 0.2
        return min(1.0, base_ratio * 0.8 + outlet_bonus)

    @staticmethod
    def calculate_score(
        room: Room,
        request: RoomRequest,
        occupancy: OccupancyIndex,
        target_date: Optional[str] = None,
    ) -> Tuple[float, Dict[str, float]]:
        date_str = target_date or request.date
        space_needed = request.space_needed

        # 1. Capacity fit penalty (tighter is better)
        cap_diff = abs(room.capacity - space_needed)
        fit_term = -0.45 * (cap_diff / 200.0)

        # 2. Facility match ratio
        facility_ratio = RoomScorer.facility_match_ratio(room, request)
        facility_term = 0.25 * facility_ratio

        # 3. Utilization term (prefer underused rooms)
        util = occupancy.get_utilization(room.room_id, date_str)
        underused_term = 0.20 * (1.0 - util)

        # 4. Preference bonus
        pref_bonus = RoomScorer.preference_bonus(room.room_id, request)
        pref_term = 0.10 * pref_bonus

        total_score = fit_term + facility_term + underused_term + pref_term

        breakdown = {
            "capacity_diff": cap_diff,
            "fit_term": fit_term,
            "facility_ratio": facility_ratio,
            "facility_term": facility_term,
            "utilization": util,
            "underused_term": underused_term,
            "pref_bonus": pref_bonus,
            "pref_term": pref_term,
            "total_score": total_score,
        }
        return total_score, breakdown

    @staticmethod
    def rank_feasible_rooms(
        rooms: List[Room],
        request: RoomRequest,
        occupancy: OccupancyIndex,
        target_date: Optional[str] = None,
    ) -> List[Tuple[Room, float, Dict[str, float]]]:
        """
        Ranks a list of feasible rooms descending by score.
        """
        scored = []
        for r in rooms:
            score, breakdown = RoomScorer.calculate_score(r, request, occupancy, target_date)
            scored.append((r, score, breakdown))

        # Sort descending by total score, then tiebreak by tighter capacity
        scored.sort(key=lambda x: (x[1], -abs(x[0].capacity - request.space_needed)), reverse=True)
        return scored


class TieBreaker:
    """
    Tie-break order (when two requests compete for the same slot):
    1. Purpose priority: exam > faculty > club > study
    2. Submission timestamp (earlier wins)
    3. Request ID (deterministic fallback)
    """

    @staticmethod
    def compare_requests(req_a: RoomRequest, req_b: RoomRequest) -> int:
        """
        Returns:
            -1 if req_a wins
             1 if req_b wins
             0 if absolute tie (same purpose, timestamp, and id)
        """
        p_a = get_purpose_score(req_a.purpose)
        p_b = get_purpose_score(req_b.purpose)
        if p_a != p_b:
            return -1 if p_a > p_b else 1

        if req_a.submitted_at != req_b.submitted_at:
            return -1 if req_a.submitted_at < req_b.submitted_at else 1

        if req_a.request_id != req_b.request_id:
            return -1 if req_a.request_id < req_b.request_id else 1

        return 0
