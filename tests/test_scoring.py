import unittest
from datetime import datetime
from allocator.models import Room, RoomRequest, RoomPreference
from allocator.occupancy import OccupancyIndex
from allocator.scoring import RoomScorer, TieBreaker


class TestScoringAndTiebreak(unittest.TestCase):
    def setUp(self):
        self.occupancy = OccupancyIndex()
        self.req = RoomRequest(
            request_id="REQ-01",
            week="2025-08-04",
            club="Robotics",
            purpose="Meeting",
            date="2025-08-04",
            start_hour=14,
            duration_hours=2,
            expected_attendance=30,
            projector_required=True,
            computers_required=False,
            preferences=[
                RoomPreference(rank=1, room_id="R101"),
                RoomPreference(rank=2, room_id="R102"),
            ],
        )
        self.room_r101 = Room("R101", "Central", 1, "Classroom", 40, True, False, True, 10)
        self.room_r102 = Room("R102", "Central", 1, "Classroom", 80, True, False, True, 10)

    def test_preference_bonus(self):
        self.assertEqual(RoomScorer.preference_bonus("R101", self.req), 1.0)
        self.assertEqual(RoomScorer.preference_bonus("R102", self.req), 0.6)
        self.assertEqual(RoomScorer.preference_bonus("R999", self.req), 0.0)

    def test_score_ranking_prefers_tighter_fit_and_preference(self):
        score_1, b1 = RoomScorer.calculate_score(self.room_r101, self.req, self.occupancy)
        score_2, b2 = RoomScorer.calculate_score(self.room_r102, self.req, self.occupancy)

        # R101 (cap 40 vs needed 30, diff 10, pref bonus 1.0) should score higher than R102 (cap 80, diff 50, pref bonus 0.6)
        self.assertGreater(score_1, score_2)

    def test_tiebreaker_purpose_priority(self):
        req_exam = RoomRequest("R-EXAM", "2025-08-04", "Dept CS", "Final Exam", "2025-08-04", 10, 2, 30, False, False)
        req_club = RoomRequest("R-CLUB", "2025-08-04", "Anime Club", "Club Meeting", "2025-08-04", 10, 2, 30, False, False)

        # Exam should win over Club (return -1)
        self.assertEqual(TieBreaker.compare_requests(req_exam, req_club), -1)
        self.assertEqual(TieBreaker.compare_requests(req_club, req_exam), 1)

    def test_tiebreaker_timestamp_priority(self):
        req_early = RoomRequest("R-01", "2025-08-04", "Club A", "Meeting", "2025-08-04", 10, 2, 30, False, False, submitted_at=datetime(2025, 8, 1, 9, 0, 0))
        req_late = RoomRequest("R-02", "2025-08-04", "Club B", "Meeting", "2025-08-04", 10, 2, 30, False, False, submitted_at=datetime(2025, 8, 1, 10, 0, 0))

        # Earlier timestamp wins
        self.assertEqual(TieBreaker.compare_requests(req_early, req_late), -1)


if __name__ == "__main__":
    unittest.main()
