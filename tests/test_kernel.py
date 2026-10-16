import unittest
from datetime import datetime
from allocator.models import Room, RoomRequest, RoomPreference
from allocator.occupancy import OccupancyIndex
from allocator.kernel import AllocationKernel


class TestAllocationKernel(unittest.TestCase):
    def setUp(self):
        self.occupancy = OccupancyIndex()
        self.rooms = {
            "R001": Room("R001", "North", 1, "Classroom", 40, True, False, True, 10),
            "R002": Room("R002", "South", 2, "Classroom", 80, True, True, True, 15),
        }
        self.kernel = AllocationKernel(self.rooms, self.occupancy)

    def test_club_cap_enforcement(self):
        # Same club submits two requests
        req1 = RoomRequest(
            "REQ-1", "2025-08-04", "Robotics Club", "Meeting 1", "2025-08-04", 10, 2, 20, True, False,
            submitted_at=datetime(2025, 8, 1, 9, 0, 0),
        )
        req2 = RoomRequest(
            "REQ-2", "2025-08-04", "Robotics Club", "Meeting 2", "2025-08-05", 14, 2, 20, True, False,
            submitted_at=datetime(2025, 8, 1, 10, 0, 0),
        )

        result = self.kernel.run("2025-08-04", [req1, req2])
        decisions_by_id = {d.request_id: d for d in result.decisions}

        # req1 is earlier -> should be active and Approved
        self.assertIn(decisions_by_id["REQ-1"].final_status, ("Approved", "Moved"))
        # req2 is later from same club -> should be Deferred
        self.assertEqual(decisions_by_id["REQ-2"].final_status, "Deferred")
        self.assertIn("CLUB_CAP_EXCEEDED", decisions_by_id["REQ-2"].reason_codes)

    def test_successful_allocation_and_occupancy_lock(self):
        req_a = RoomRequest(
            "REQ-A", "2025-08-04", "Club Alpha", "Workshop", "2025-08-04", 10, 2, 30, True, False,
            preferences=[RoomPreference(1, "R001")],
            submitted_at=datetime(2025, 8, 1, 9, 0, 0),
        )
        req_b = RoomRequest(
            "REQ-B", "2025-08-04", "Club Beta", "Workshop", "2025-08-04", 10, 2, 30, True, False,
            preferences=[RoomPreference(1, "R001")],  # Also prefers R001 at same time
            submitted_at=datetime(2025, 8, 1, 9, 30, 0),
        )

        result = self.kernel.run("2025-08-04", [req_a, req_b])
        decisions_by_id = {d.request_id: d for d in result.decisions}

        # Req A submitted earlier -> gets R001 Approved
        self.assertEqual(decisions_by_id["REQ-A"].final_status, "Approved")
        self.assertEqual(decisions_by_id["REQ-A"].assigned_room, "R001")

        # Req B clashing -> gets Relocated (Moved) to R002
        self.assertEqual(decisions_by_id["REQ-B"].final_status, "Moved")
        self.assertEqual(decisions_by_id["REQ-B"].assigned_room, "R002")


if __name__ == "__main__":
    unittest.main()
