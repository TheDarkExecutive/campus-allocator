import unittest
from datetime import datetime
from allocator.models import ClassSchedule, Event
from allocator.occupancy import OccupancyIndex


class TestOccupancyIndex(unittest.TestCase):
    def setUp(self):
        self.occupancy = OccupancyIndex()
        self.schedules = [
            ClassSchedule(
                schedule_id="CS101-1",
                room_id="R001",
                course_code="CS101",
                weekday="Mon",
                start_hour=9,
                duration_hours=2,
                expected_attendance=30,
                department="Computer Science",
            )
        ]
        self.events = [
            Event(
                event_id="EVT-01",
                room_id="R001",
                event_type="Seminar",
                start_time=datetime(2025, 8, 4, 14, 0, 0),  # Monday 14:00
                duration_hours=2,
                expected_attendance=50,
            )
        ]
        self.occupancy.build_from_data("2025-08-04", self.schedules, self.events)

    def test_occupied_slots(self):
        # Mon 9:00 and 10:00 should be busy with CS101
        self.assertFalse(self.occupancy.is_slot_free("R001", "2025-08-04", 9, 2))
        self.assertFalse(self.occupancy.is_slot_free("R001", "2025-08-04", 10, 1))

        # Mon 14:00 and 15:00 should be busy with Event
        self.assertFalse(self.occupancy.is_slot_free("R001", "2025-08-04", 14, 2))

    def test_free_slots(self):
        # Mon 11:00 should be free
        self.assertTrue(self.occupancy.is_slot_free("R001", "2025-08-04", 11, 2))
        # Another room should be free
        self.assertTrue(self.occupancy.is_slot_free("R002", "2025-08-04", 9, 2))

    def test_utilization_calculation(self):
        # Window 8-20 has 12 hours. Hours 9, 10, 14, 15 are busy -> 4 hours busy
        # 4 / 12 = 0.333
        util = self.occupancy.get_utilization("R001", "2025-08-04", window_start=8, window_end=20)
        self.assertAlmostEqual(util, 4.0 / 12.0, places=3)
        self.assertTrue(0.0 <= util <= 1.0)


if __name__ == "__main__":
    unittest.main()
