from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Any, Optional

from .models import Room, RoomRequest
from .occupancy import OccupancyIndex
from .feasibility import FeasibilityFilter
from .scoring import RoomScorer


@dataclass
class ReplayMetrics:
    total_evaluated: int = 0
    total_matches: int = 0
    overall_agreement: float = 0.0

    approved_total: int = 0
    approved_matches: int = 0
    approved_pct: float = 0.0

    rejected_total: int = 0
    rejected_matches: int = 0
    rejected_pct: float = 0.0

    waitlisted_total: int = 0
    waitlisted_matches: int = 0
    waitlisted_pct: float = 0.0

    mismatches: List[Dict[str, Any]] = field(default_factory=list)


class ReplayValidator:
    """
    Validates kernel decisions against historical ground-truth outcome labels in data/room_requests.csv.
    """

    def __init__(self, rooms: Dict[str, Room], occupancy: OccupancyIndex) -> None:
        self.rooms = rooms
        self.occupancy = occupancy

    def evaluate_request(self, req: RoomRequest) -> str:
        """
        Determines predicted outcome for a single historical request.
        """
        feasible = FeasibilityFilter.find_feasible_rooms(
            self.rooms, req, self.occupancy, req.date, req.start_hour
        )
        if not feasible:
            # Try alternate hours
            found_alt = False
            for h in range(8, 20):
                if h == req.start_hour:
                    continue
                if FeasibilityFilter.find_feasible_rooms(self.rooms, req, self.occupancy, req.date, h):
                    found_alt = True
                    break
            if found_alt:
                return "Waitlisted"  # Or Moved
            return "Rejected"
        else:
            return "Approved"

    def run_replay(self, historical_requests: List[RoomRequest], max_samples: Optional[int] = None) -> ReplayMetrics:
        metrics = ReplayMetrics()
        eval_set = historical_requests[:max_samples] if max_samples else historical_requests

        for req in eval_set:
            actual_status = (req.status or "Approved").capitalize()
            if actual_status not in ("Approved", "Rejected", "Waitlisted"):
                actual_status = "Approved"

            predicted_status = self.evaluate_request(req)

            metrics.total_evaluated += 1

            is_match = False
            if actual_status == "Approved":
                metrics.approved_total += 1
                if predicted_status in ("Approved", "Moved"):
                    metrics.approved_matches += 1
                    is_match = True
            elif actual_status == "Rejected":
                metrics.rejected_total += 1
                if predicted_status == "Rejected":
                    metrics.rejected_matches += 1
                    is_match = True
            elif actual_status == "Waitlisted":
                metrics.waitlisted_total += 1
                if predicted_status in ("Waitlisted", "Moved"):
                    metrics.waitlisted_matches += 1
                    is_match = True

            if is_match:
                metrics.total_matches += 1
            else:
                if len(metrics.mismatches) < 50:
                    metrics.mismatches.append({
                        "request_id": req.request_id,
                        "date": req.date,
                        "hour": req.start_hour,
                        "capacity": req.space_needed,
                        "actual": actual_status,
                        "predicted": predicted_status,
                    })

        # Calculate percentages
        if metrics.total_evaluated > 0:
            metrics.overall_agreement = (metrics.total_matches / metrics.total_evaluated) * 100.0

        if metrics.approved_total > 0:
            metrics.approved_pct = (metrics.approved_matches / metrics.approved_total) * 100.0

        if metrics.rejected_total > 0:
            metrics.rejected_pct = (metrics.rejected_matches / metrics.rejected_total) * 100.0

        if metrics.waitlisted_total > 0:
            metrics.waitlisted_pct = (metrics.waitlisted_matches / metrics.waitlisted_total) * 100.0

        return metrics
