import unittest
from allocator.models import Room, RoomRequest
from allocator.exceptions import ExceptionDetector


class TestExceptionDetection(unittest.TestCase):
    def test_tight_fit_detection(self):
        room = Room("R010", "North", 1, "Classroom", 40, True, False, True, 10)
        # Needs 38 space -> 2 spare seats (<= 3 is tight fit)
        req = RoomRequest("REQ-TF", "2025-08-04", "Drama", "Auditions", "2025-08-04", 10, 2, 38, False, False)

        exc = ExceptionDetector.check_tight_fit(room, req)
        self.assertIsNotNone(exc)
        self.assertEqual(exc.exception_type, "TIGHT_FIT")

    def test_no_tight_fit_when_spacious(self):
        room = Room("R010", "North", 1, "Classroom", 60, True, False, True, 10)
        # Needs 40 space -> 20 spare seats (> 3 is not tight)
        req = RoomRequest("REQ-OK", "2025-08-04", "Drama", "Auditions", "2025-08-04", 10, 2, 40, False, False)

        exc = ExceptionDetector.check_tight_fit(room, req)
        self.assertIsNone(exc)

    def test_manual_flag_detection(self):
        req_flagged = RoomRequest(
            "REQ-FLG", "2025-08-04", "Debate", "Guest Lecture", "2025-08-04", 10, 2, 30, False, False,
            notes="Please escalate to dean for special permission"
        )
        exc = ExceptionDetector.check_manual_flags(req_flagged)
        self.assertIsNotNone(exc)
        self.assertEqual(exc.exception_type, "MANUAL_FLAG")


if __name__ == "__main__":
    unittest.main()
