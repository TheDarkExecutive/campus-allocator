import unittest
from allocator.models import Room, RoomRequest
from allocator.occupancy import OccupancyIndex
from allocator.feasibility import FeasibilityFilter


class TestFeasibilityFilter(unittest.TestCase):
    def setUp(self):
        self.occupancy = OccupancyIndex()
        self.room = Room(
            room_id="R101",
            building="Central",
            floor=2,
            room_type="Classroom",
            capacity=50,
            projector=True,
            computers=False,
            accessible=True,
            power_outlets=12,
        )

    def test_capacity_feasibility(self):
        # 40 attendees + 4 chairs + 2*3 tables = 50 units (exact fit)
        req = RoomRequest(
            request_id="REQ-01",
            week="2025-08-04",
            club="Math Club",
            purpose="Meeting",
            date="2025-08-04",
            start_hour=10,
            duration_hours=2,
            expected_attendance=40,
            extra_chairs=4,
            extra_tables=2,
            projector_required=True,
            computers_required=False,
        )
        is_ok, reasons, _ = FeasibilityFilter.evaluate(self.room, req, self.occupancy)
        self.assertTrue(is_ok)
        self.assertIn("FEASIBLE", reasons)

    def test_capacity_deficit(self):
        # 45 attendees + 4 chairs + 2*3 tables = 55 units > 50 capacity
        req = RoomRequest(
            request_id="REQ-02",
            week="2025-08-04",
            club="Math Club",
            purpose="Meeting",
            date="2025-08-04",
            start_hour=10,
            duration_hours=2,
            expected_attendance=45,
            extra_chairs=4,
            extra_tables=2,
            projector_required=False,
            computers_required=False,
        )
        is_ok, reasons, _ = FeasibilityFilter.evaluate(self.room, req, self.occupancy)
        self.assertFalse(is_ok)
        self.assertIn("CAPACITY_DEFICIT", reasons)

    def test_missing_computers(self):
        req = RoomRequest(
            request_id="REQ-03",
            week="2025-08-04",
            club="Coding Club",
            purpose="Hackathon",
            date="2025-08-04",
            start_hour=10,
            duration_hours=2,
            expected_attendance=20,
            projector_required=False,
            computers_required=True,  # Room has False
        )
        is_ok, reasons, _ = FeasibilityFilter.evaluate(self.room, req, self.occupancy)
        self.assertFalse(is_ok)
        self.assertIn("NO_COMPUTERS", reasons)

    def test_schedule_clash(self):
        self.occupancy.mark_allocated("R101", "2025-08-04", 10, 2, "OTHER-REQ")
        req = RoomRequest(
            request_id="REQ-04",
            week="2025-08-04",
            club="Chess Club",
            purpose="Tournament",
            date="2025-08-04",
            start_hour=10,
            duration_hours=2,
            expected_attendance=20,
            projector_required=False,
            computers_required=False,
        )
        is_ok, reasons, _ = FeasibilityFilter.evaluate(self.room, req, self.occupancy)
        self.assertFalse(is_ok)
        self.assertIn("SCHEDULE_CLASH", reasons)


if __name__ == "__main__":
    unittest.main()
