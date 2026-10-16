from __future__ import annotations

from typing import List, Dict, Optional, Tuple, Set
from collections import defaultdict
from datetime import datetime

from .models import (
    Room,
    RoomRequest,
    Decision,
    ExceptionCase,
    AllocationResult,
    OccupancySlot,
)
from .occupancy import OccupancyIndex
from .feasibility import FeasibilityFilter
from .scoring import RoomScorer, TieBreaker
from .explain import ExplanationBuilder
from .exceptions import ExceptionDetector


class AllocationKernel:
    """
    Deterministic campus room allocation kernel.
    Zero external APIs. Deterministic matching with rule trace.
    """

    def __init__(self, rooms: Dict[str, Room], occupancy: OccupancyIndex) -> None:
        self.rooms = rooms
        self.occupancy = occupancy

    def run(self, week_str: str, requests: List[RoomRequest]) -> AllocationResult:
        decisions: List[Decision] = []
        exceptions: List[ExceptionCase] = []
        flags: List[str] = []

        # -------------------------------------------------------------------------
        # 1. CLUB CAP FILTER: 1 ACTIVE REQUEST PER CLUB PER WEEK
        # -------------------------------------------------------------------------
        requests_by_club: Dict[str, List[RoomRequest]] = defaultdict(list)
        for req in requests:
            requests_by_club[req.club].append(req)

        active_requests: List[RoomRequest] = []
        deferred_requests: List[RoomRequest] = []

        for club_name, club_reqs in requests_by_club.items():
            # Sort by submission timestamp (earliest wins the active slot)
            club_reqs.sort(key=lambda r: (r.submitted_at, r.request_id))
            active_requests.append(club_reqs[0])

            if len(club_reqs) > 1:
                for def_req in club_reqs[1:]:
                    deferred_requests.append(def_req)
                    why_text, trace = ExplanationBuilder.build_deferred_why(
                        def_req, f"Club cap: active slot already held by {club_reqs[0].request_id}"
                    )
                    decisions.append(
                        Decision(
                            request_id=def_req.request_id,
                            club=def_req.club,
                            final_status="Deferred",
                            assigned_room=None,
                            assigned_date=None,
                            assigned_hour=None,
                            reason_codes=["CLUB_CAP_EXCEEDED"],
                            rule_trace=trace,
                            decided_by="kernel",
                            why=why_text,
                        )
                    )

        # -------------------------------------------------------------------------
        # 2. SORT ACTIVE REQUESTS BY GLOBAL TIEBREAK PRIORITY
        # -------------------------------------------------------------------------
        active_requests.sort(
            key=lambda r: (
                -TieBreaker.compare_requests(r, r),  # dummy tiebreaker baseline
                r.submitted_at,
                r.request_id,
            )
        )

        # Bubble-sort / sort with TieBreaker comparator
        from functools import cmp_to_key
        active_requests.sort(key=cmp_to_key(TieBreaker.compare_requests))

        # -------------------------------------------------------------------------
        # 3. ALLOCATION PASS
        # -------------------------------------------------------------------------
        allocated_slots: Set[Tuple[str, str, int]] = set()

        for req in active_requests:
            # Check for manual flags in notes
            flag_exc = ExceptionDetector.check_manual_flags(req)
            if flag_exc:
                exceptions.append(flag_exc)
                flags.append(f"Manual flag on {req.club} ({req.request_id}): {req.notes}")

            # Check for late submission (after target date)
            try:
                from dateutil import parser as dt_parser
                req_date_obj = dt_parser.parse(req.date).date()
                if req.submitted_at.date() > req_date_obj:
                    late_exc = ExceptionCase(
                        exception_id=f"EXC-LATE-{req.request_id}",
                        request=req,
                        exception_type="LATE_SUBMISSION",
                        situation=f"Submission timestamp {req.submitted_at.isoformat()} arrived after scheduled event date {req.date}.",
                        auto_pick=None,
                    )
                    exceptions.append(late_exc)
                    flags.append(f"Late submission detected for {req.club} ({req.request_id})")
            except Exception:
                pass

            assigned_room: Optional[Room] = None
            assigned_status = "Approved"
            decision_trace: List[str] = []
            chosen_breakdown: Optional[Dict[str, float]] = None
            is_relocated = False

            # Step A: Check explicit preference ranking (Rank 1, Rank 2, Rank 3)
            for pref in req.preferences:
                target_room = self.rooms.get(pref.room_id)
                if target_room:
                    is_ok, _, trace = FeasibilityFilter.evaluate(
                        target_room, req, self.occupancy, req.date, req.start_hour
                    )
                    if is_ok:
                        assigned_room = target_room
                        if pref.rank > 1:
                            assigned_status = "Moved"
                            is_relocated = True
                        decision_trace = trace
                        _, chosen_breakdown = RoomScorer.calculate_score(target_room, req, self.occupancy, req.date)
                        break

            # Step B: If preferences unavailable, find best feasible room at same date/hour
            if assigned_room is None:
                feasible_rooms = FeasibilityFilter.find_feasible_rooms(
                    self.rooms, req, self.occupancy, req.date, req.start_hour
                )
                if feasible_rooms:
                    ranked = RoomScorer.rank_feasible_rooms(
                        [r for r, _ in feasible_rooms], req, self.occupancy, req.date
                    )
                    assigned_room = ranked[0][0]
                    chosen_breakdown = ranked[0][2]
                    assigned_status = "Moved"
                    is_relocated = True
                    decision_trace = [f"Preference fallback -> best scoring feasible room {assigned_room.room_id}"]

            # Step C: If still no room at requested hour, try other hours the same day (window 8-20)
            if assigned_room is None:
                for candidate_hour in range(8, 20):
                    if candidate_hour == req.start_hour:
                        continue
                    feasible_at_h = FeasibilityFilter.find_feasible_rooms(
                        self.rooms, req, self.occupancy, req.date, candidate_hour
                    )
                    if feasible_at_h:
                        ranked_h = RoomScorer.rank_feasible_rooms(
                            [r for r, _ in feasible_at_h], req, self.occupancy, req.date
                        )
                        assigned_room = ranked_h[0][0]
                        chosen_breakdown = ranked_h[0][2]
                        assigned_status = "Moved"
                        is_relocated = True
                        req.start_hour = candidate_hour  # Adjusted hour
                        decision_trace = [f"Hour shifted to {candidate_hour}:00 to accommodate slot"]
                        break

            # Step D: Finalize Decision or Reject
            if assigned_room is not None:
                # Mark occupied in occupancy index
                self.occupancy.mark_allocated(
                    assigned_room.room_id, req.date, req.start_hour, req.duration_hours, req.request_id
                )

                # Check for tight fit anomaly
                tight_exc = ExceptionDetector.check_tight_fit(assigned_room, req)
                if tight_exc:
                    exceptions.append(tight_exc)
                    flags.append(f"Tight fit in {assigned_room.room_id} for {req.club}: spare seats <= 3")

                why_str, trace = ExplanationBuilder.build_approval_why(
                    assigned_room,
                    req,
                    self.occupancy,
                    score_breakdown=chosen_breakdown,
                    is_moved=is_relocated,
                )

                decisions.append(
                    Decision(
                        request_id=req.request_id,
                        club=req.club,
                        final_status=assigned_status,
                        assigned_room=assigned_room.room_id,
                        assigned_date=req.date,
                        assigned_hour=req.start_hour,
                        reason_codes=["FEASIBLE_MATCH", "PREFERENCE_SATISFIED" if not is_relocated else "RELOCATED_FALLBACK"],
                        rule_trace=decision_trace + trace,
                        decided_by="kernel",
                        why=why_str,
                    )
                )
            else:
                # Infeasible
                no_feas_exc = ExceptionDetector.check_no_feasible(req, list(self.rooms.keys()))
                exceptions.append(no_feas_exc)
                flags.append(f"Infeasible request: {req.club} ({req.request_id}) on {req.date}")

                why_str, trace = ExplanationBuilder.build_rejection_why(
                    req,
                    [
                        f"No available room fits capacity {req.space_needed} on {req.date} at hour {req.start_hour}",
                        f"Projector required: {req.projector_required}, Computers required: {req.computers_required}",
                        "All alternative hours in [8:00-20:00] occupied",
                    ],
                )
                decisions.append(
                    Decision(
                        request_id=req.request_id,
                        club=req.club,
                        final_status="Rejected",
                        assigned_room=None,
                        assigned_date=req.date,
                        assigned_hour=req.start_hour,
                        reason_codes=["NO_FEASIBLE_ROOM", "CAPACITY_OR_FACILITY_SHORTAGE"],
                        rule_trace=trace,
                        decided_by="kernel",
                        why=why_str,
                    )
                )

        return AllocationResult(
            week=week_str,
            decisions=decisions,
            exceptions=exceptions,
            flags=flags,
        )
