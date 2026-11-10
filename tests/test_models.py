from datetime import datetime, timezone
import unittest

from integrity_analytics.domain.models import Telemetry


def telemetry(asset_id: str, event_id: str) -> Telemetry:
    return Telemetry(
        asset_id=asset_id,
        event_id=event_id,
        observed_at=datetime(2026, 10, 18, 12, 0, tzinfo=timezone.utc),
        measurements={"temperature": 20.0},
        source="test",
    )


class DiagnosticFonteIdTests(unittest.TestCase):
    def test_same_event_maps_to_same_id_for_idempotent_retries(self) -> None:
        self.assertEqual(
            telemetry("asset", "event-1").diagnostic_fonte_id(),
            telemetry("asset", "event-1").diagnostic_fonte_id(),
        )

    def test_distinct_events_map_to_distinct_ids(self) -> None:
        ids = {telemetry("asset", f"event-{i}").diagnostic_fonte_id() for i in range(1000)}
        ids.add(telemetry("other-asset", "event-1").diagnostic_fonte_id())
        self.assertEqual(len(ids), 1001)

    def test_id_fits_oprs_positive_int64(self) -> None:
        for i in range(1000):
            fonte_id = telemetry("asset", f"event-{i}").diagnostic_fonte_id()
            self.assertGreater(fonte_id, 0)
            self.assertLess(fonte_id, 2**63)


if __name__ == "__main__":
    unittest.main()
