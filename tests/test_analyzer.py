from datetime import datetime, timezone
import math
import unittest

from integrity_analytics.config import MeasurementRule
from integrity_analytics.domain.analyzer import RuleBasedIntegrityAnalyzer, TelemetryValidationError
from integrity_analytics.domain.models import Telemetry


class AnalyzerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.analyzer = RuleBasedIntegrityAnalyzer(
            {"temperature": MeasurementRule(10.0, 30.0), "pressure": MeasurementRule(100.0, 200.0)},
            (0.05, 0.15, 0.30),
        )

    def telemetry(self, measurements: dict[str, float]) -> Telemetry:
        return Telemetry(
            asset_id="asset-01",
            event_id="event-01",
            observed_at=datetime.now(timezone.utc),
            measurements=measurements,
            source="test",
        )

    def test_values_inside_limits_are_severity_one(self) -> None:
        result = self.analyzer.analyze(self.telemetry({"temperature": 20, "pressure": 150}))
        self.assertEqual(result.severity, 1)
        self.assertEqual(result.score, 0)
        self.assertEqual(result.anomalous_measurements, {})

    def test_outside_limits_is_normalized_by_rule_range(self) -> None:
        result = self.analyzer.analyze(self.telemetry({"temperature": 34, "pressure": 150}))
        self.assertAlmostEqual(result.score, 0.2)
        self.assertEqual(result.severity, 4)
        self.assertIn("temperature", result.anomalous_measurements)

    def test_unknown_measurement_is_rejected(self) -> None:
        with self.assertRaises(TelemetryValidationError):
            self.analyzer.analyze(self.telemetry({"vibration": 3.0}))

    def test_non_finite_measurement_is_rejected(self) -> None:
        with self.assertRaises(TelemetryValidationError):
            self.analyzer.analyze(self.telemetry({"temperature": math.nan}))

    def test_empty_measurements_are_rejected(self) -> None:
        with self.assertRaises(TelemetryValidationError):
            self.analyzer.analyze(self.telemetry({}))


if __name__ == "__main__":
    unittest.main()
