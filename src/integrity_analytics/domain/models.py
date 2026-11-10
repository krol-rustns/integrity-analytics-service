from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib


@dataclass(frozen=True)
class Telemetry:
    asset_id: str
    event_id: str
    observed_at: datetime
    measurements: dict[str, float]
    source: str

    def diagnostic_fonte_id(self) -> int:
        digest = hashlib.sha256(f"{self.asset_id}\0{self.event_id}".encode()).digest()
        return int.from_bytes(digest[:8], "big") >> 1 or 1


@dataclass(frozen=True)
class AnalysisResult:
    score: float
    severity: int
    anomalous_measurements: dict[str, float]
    evaluated_measurements: int
