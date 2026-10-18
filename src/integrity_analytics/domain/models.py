from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Telemetry:
    asset_id: str
    event_id: str
    observed_at: datetime
    measurements: dict[str, float]
    source: str


@dataclass(frozen=True)
class AnalysisResult:
    score: float
    severity: int
    anomalous_measurements: dict[str, float]
    evaluated_measurements: int
