import math
from integrity_analytics.config import MeasurementRule
from integrity_analytics.domain.models import AnalysisResult, Telemetry


class TelemetryValidationError(ValueError):
    pass


class RuleBasedIntegrityAnalyzer:
    def __init__(
        self,
        rules: dict[str, MeasurementRule],
        severity_thresholds: tuple[float, float, float],
    ) -> None:
        if not rules:
            raise ValueError("Ao menos uma regra de medição deve ser configurada")
        self.rules = rules
        self.severity_thresholds = severity_thresholds

    def analyze(self, telemetry: Telemetry) -> AnalysisResult:
        if not telemetry.asset_id.strip():
            raise TelemetryValidationError("asset_id ausente")
        if not telemetry.event_id.strip():
            raise TelemetryValidationError("event_id ausente")
        if not telemetry.measurements:
            raise TelemetryValidationError("telemetria sem medições")
        observed = 0
        anomalies: dict[str, float] = {}
        scores: list[float] = []
        unknown = sorted(set(telemetry.measurements) - set(self.rules))
        if unknown:
            raise TelemetryValidationError(
                f"Medições sem regra configurada: {', '.join(unknown)}"
            )
        for name, value in telemetry.measurements.items():
            if not math.isfinite(value):
                raise TelemetryValidationError(f"Medição não finita: {name}")
            rule = self.rules[name]
            observed += 1
            if value < rule.minimum:
                deviation = (rule.minimum - value) / (rule.maximum - rule.minimum)
            elif value > rule.maximum:
                deviation = (value - rule.maximum) / (rule.maximum - rule.minimum)
            else:
                deviation = 0.0
            scores.append(deviation)
            if deviation > 0:
                anomalies[name] = deviation
        score = max(scores, default=0.0)
        t1, t2, t3 = self.severity_thresholds
        if score == 0:
            severity = 1
        elif score <= t1:
            severity = 2
        elif score <= t2:
            severity = 3
        elif score <= t3:
            severity = 4
        else:
            severity = 5
        return AnalysisResult(
            score=score,
            severity=severity,
            anomalous_measurements=anomalies,
            evaluated_measurements=observed,
        )
