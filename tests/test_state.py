from datetime import datetime, timedelta, timezone
import tempfile
import unittest
from pathlib import Path

from integrity_analytics.infrastructure.state import EventState


class EventStateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = str(Path(self.temp_dir.name) / "state.sqlite3")
        self.state = EventState(self.database)
        self.now = datetime(2026, 10, 18, 12, 0, tzinfo=timezone.utc)

    def tearDown(self) -> None:
        self.state.close()
        self.temp_dir.cleanup()

    def test_event_status_is_durable(self) -> None:
        self.state.record("asset", "event", self.now, "below_threshold", "severity=1")
        self.assertEqual(self.state.status("asset", "event"), "below_threshold")

    def test_watermark_uses_initial_value_until_checkpoint_exists(self) -> None:
        self.assertEqual(self.state.watermark("asset", self.now), self.now)

    def test_watermark_only_moves_forward(self) -> None:
        self.state.advance_watermark("asset", self.now + timedelta(minutes=2))
        self.state.advance_watermark("asset", self.now)
        self.assertEqual(self.state.watermark("asset", self.now), self.now + timedelta(minutes=2))

    def test_pending_event_survives_reopening_database(self) -> None:
        self.state.record("asset", "event", self.now, "diagnostic_pending", "in flight")
        self.state.close()
        self.state = EventState(self.database)
        self.assertEqual(self.state.status("asset", "event"), "diagnostic_pending")


if __name__ == "__main__":
    unittest.main()
