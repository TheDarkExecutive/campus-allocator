from __future__ import annotations

from datetime import datetime, date, timedelta
from typing import Dict, Tuple, List, Optional
from dateutil import parser as dt_parser

from .models import ClassSchedule, Event, OccupancySlot


WEEKDAY_MAP = {
    "mon": 0,
    "tue": 1,
    "wed": 2,
    "thu": 3,
    "fri": 4,
    "sat": 5,
    "sun": 6,
}


class OccupancyIndex:
    """
    Occupancy index keyed by (room_id, ISO_date, hour).
    Maps to occupancy source type: "class", "event", or "allocated".
    """

    def __init__(self) -> None:
        # Key: (room_id, ISO_date_str, hour_int) -> OccupancySlot
        self._index: Dict[Tuple[str, str, int], OccupancySlot] = {}

    def build_from_data(
        self,
        week_start_str: str,
        class_schedules: List[ClassSchedule],
        events: List[Event],
    ) -> None:
        """
        Builds the occupancy index for a target week starting at week_start_str.
        """
        self._index.clear()

        # Parse target week start date
        try:
            week_start_dt = dt_parser.parse(week_start_str).date()
        except Exception:
            week_start_dt = date.today()

        # Align to Monday if week_start is given as Monday or Sunday
        # In campus scheduling, weekday in {Mon,Tue,Wed,Thu,Fri,Sat}
        # We determine base monday:
        if week_start_dt.weekday() != 0:
            # Shift to Monday of that week
            monday_dt = week_start_dt - timedelta(days=week_start_dt.weekday())
        else:
            monday_dt = week_start_dt

        # 1. Index Class Schedules
        for cs in class_schedules:
            day_offset = WEEKDAY_MAP.get(cs.weekday.lower()[:3], 0)
            target_date = monday_dt + timedelta(days=day_offset)
            date_str = target_date.isoformat()

            for h in range(cs.start_hour, cs.start_hour + cs.duration_hours):
                key = (cs.room_id, date_str, h)
                self._index[key] = OccupancySlot(
                    room_id=cs.room_id,
                    date=date_str,
                    hour=h,
                    source_type="class",
                    reference_id=cs.course_code,
                )

        # 2. Index Events
        # Target week range: Monday to Sunday
        week_end_dt = monday_dt + timedelta(days=6)
        for ev in events:
            ev_date = ev.start_time.date()
            if monday_dt <= ev_date <= week_end_dt:
                date_str = ev_date.isoformat()
                ev_start_hour = ev.start_time.hour
                for h in range(ev_start_hour, ev_start_hour + ev.duration_hours):
                    key = (ev.room_id, date_str, h)
                    # Events can overwrite or share conflict, we mark as event
                    self._index[key] = OccupancySlot(
                        room_id=ev.room_id,
                        date=date_str,
                        hour=h,
                        source_type="event",
                        reference_id=ev.event_id,
                    )

    def is_slot_free(self, room_id: str, date_str: str, start_hour: int, duration_hours: int) -> bool:
        """Returns True if every hour in [start_hour, start_hour + duration_hours) is unoccupied."""
        for h in range(start_hour, start_hour + duration_hours):
            if (room_id, date_str, h) in self._index:
                return False
        return True

    def get_clashes(self, room_id: str, date_str: str, start_hour: int, duration_hours: int) -> List[OccupancySlot]:
        """Returns list of occupied slots colliding with the requested window."""
        clashes: List[OccupancySlot] = []
        for h in range(start_hour, start_hour + duration_hours):
            slot = self._index.get((room_id, date_str, h))
            if slot is not None:
                clashes.append(slot)
        return clashes

    def mark_allocated(self, room_id: str, date_str: str, start_hour: int, duration_hours: int, reference_id: str) -> None:
        """Marks a block of hours as allocated to a request."""
        for h in range(start_hour, start_hour + duration_hours):
            self._index[(room_id, date_str, h)] = OccupancySlot(
                room_id=room_id,
                date=date_str,
                hour=h,
                source_type="allocated",
                reference_id=reference_id,
            )

    def release_allocated(self, room_id: str, date_str: str, start_hour: int, duration_hours: int) -> None:
        """Releases an allocated slot."""
        for h in range(start_hour, start_hour + duration_hours):
            key = (room_id, date_str, h)
            if key in self._index and self._index[key].source_type == "allocated":
                del self._index[key]

    def busy_hours_count(self, room_id: str, date_str: str, window_start: int = 8, window_end: int = 20) -> int:
        """Counts busy hours for a room on a given date inside the 8-20 window (hours 8..19)."""
        count = 0
        for h in range(window_start, window_end):
            if (room_id, date_str, h) in self._index:
                count += 1
        return count

    def get_utilization(self, room_id: str, date_str: str, window_start: int = 8, window_end: int = 20) -> float:
        """
        Utilization(room_id, date) = busy_hours(room, date) / 12.0, clamped to [0, 1].
        """
        busy = self.busy_hours_count(room_id, date_str, window_start, window_end)
        total_window_hours = float(max(1, window_end - window_start))
        raw_util = busy / total_window_hours
        return max(0.0, min(1.0, raw_util))

    def get_room_weekly_utilization(self, room_id: str, week_start_str: str) -> float:
        """Average utilization across Mon-Sat for dashboard ranking."""
        try:
            week_start_dt = dt_parser.parse(week_start_str).date()
        except Exception:
            week_start_dt = date.today()
        if week_start_dt.weekday() != 0:
            monday_dt = week_start_dt - timedelta(days=week_start_dt.weekday())
        else:
            monday_dt = week_start_dt

        daily_utils = []
        for d in range(6):  # Mon through Sat
            day_str = (monday_dt + timedelta(days=d)).isoformat()
            daily_utils.append(self.get_utilization(room_id, day_str))
        return sum(daily_utils) / len(daily_utils) if daily_utils else 0.0

    def get_peak_hours(self, week_start_str: str) -> List[Tuple[int, int]]:
        """Returns list of (hour, total_bookings_across_all_rooms) sorted by busyness."""
        try:
            week_start_dt = dt_parser.parse(week_start_str).date()
        except Exception:
            week_start_dt = date.today()
        if week_start_dt.weekday() != 0:
            monday_dt = week_start_dt - timedelta(days=week_start_dt.weekday())
        else:
            monday_dt = week_start_dt

        week_dates = {(monday_dt + timedelta(days=d)).isoformat() for d in range(7)}
        hour_counts: Dict[int, int] = {h: 0 for h in range(8, 22)}

        for (_, d_str, h), _ in self._index.items():
            if d_str in week_dates and h in hour_counts:
                hour_counts[h] += 1

        sorted_hours = sorted(hour_counts.items(), key=lambda x: x[1], reverse=True)
        return sorted_hours
