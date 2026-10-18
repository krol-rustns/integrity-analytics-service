import logging
import threading
from datetime import datetime, timedelta, timezone
import grpc
from integrity_analytics.config import Settings
from integrity_analytics.domain.analyzer import RuleBasedIntegrityAnalyzer, TelemetryValidationError
from integrity_analytics.domain.models import Telemetry
from integrity_analytics.infrastructure.grpc.diagnostics_client import DiagnosticsClient
from integrity_analytics.infrastructure.grpc.operational_client import OperationalTelemetryClient
from integrity_analytics.infrastructure.state import EventState

logger = logging.getLogger("integrity_analytics")


class IntegrityMonitor:
    TERMINAL_STATUSES = {"submitted", "below_threshold", "rejected", "asset_mismatch"}

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.analyzer = RuleBasedIntegrityAnalyzer(settings.measurement_rules, settings.severity_thresholds)
        self.operational = OperationalTelemetryClient(settings)
        self.diagnostics = DiagnosticsClient(settings)
        self.state = EventState(settings.state_path)
        self.stop_event = threading.Event()
        self._closed = False

    def _record_rejection(self, telemetry: Telemetry, reason: str) -> None:
        if telemetry.event_id:
            self.state.record(telemetry.asset_id or self.settings.asset_id, telemetry.event_id,
                              telemetry.observed_at, "rejected", reason)
        logger.warning("telemetry_rejected_by_analyzer", extra={
            "asset_id": telemetry.asset_id, "event_id": telemetry.event_id, "reason": reason
        })

    def process(self, telemetry: Telemetry) -> None:
        if not telemetry.event_id.strip():
            logger.error("telemetry_without_event_id_cannot_be_deduplicated", extra={
                "asset_id": telemetry.asset_id, "observed_at": telemetry.observed_at.isoformat()
            })
            return
        status = self.state.status(telemetry.asset_id, telemetry.event_id)
        if status in self.TERMINAL_STATUSES:
            return
        if status in {"diagnostic_pending", "diagnostic_uncertain"}:
            logger.error("diagnostic_requires_reconciliation", extra={
                "asset_id": telemetry.asset_id, "event_id": telemetry.event_id, "state": status
            })
            return
        if telemetry.asset_id != self.settings.asset_id:
            self.state.record(telemetry.asset_id, telemetry.event_id, telemetry.observed_at,
                              "asset_mismatch", "asset_id diferente do configurado")
            logger.warning("telemetry_asset_mismatch", extra={
                "configured_asset_id": self.settings.asset_id, "received_asset_id": telemetry.asset_id
            })
            return
        try:
            result = self.analyzer.analyze(telemetry)
        except TelemetryValidationError as exc:
            self._record_rejection(telemetry, str(exc))
            return
        logger.info("telemetry_analyzed", extra={
            "asset_id": telemetry.asset_id, "event_id": telemetry.event_id,
            "score": result.score, "severity": result.severity,
            "anomalous_measurements": sorted(result.anomalous_measurements),
            "evaluated_measurements": result.evaluated_measurements,
        })
        if result.severity < self.settings.send_min_severity:
            self.state.record(telemetry.asset_id, telemetry.event_id, telemetry.observed_at,
                              "below_threshold", f"severity={result.severity}")
            return
        anomalous_names = ", ".join(sorted(result.anomalous_measurements))
        description = (
            f"Análise de integridade do ativo {telemetry.asset_id}: severidade {result.severity}; "
            f"score normalizado {result.score:.6f}; medições fora dos limites: "
            f"{anomalous_names or 'nenhuma'}; evento {telemetry.event_id}; "
            f"observado em {telemetry.observed_at.isoformat()}. "
            "Classificação baseada nas regras configuradas; requer validação operacional."
        )
        self.state.record(telemetry.asset_id, telemetry.event_id, telemetry.observed_at,
                          "diagnostic_pending", "Envio iniciado; resultado ainda não confirmado")
        try:
            diagnostic_id = self.diagnostics.register(description, result.severity)
        except grpc.RpcError as exc:
            self.state.record(telemetry.asset_id, telemetry.event_id, telemetry.observed_at,
                              "diagnostic_uncertain", f"gRPC {exc.code()}: {exc.details()}")
            logger.exception("diagnostic_result_uncertain", extra={
                "asset_id": telemetry.asset_id, "event_id": telemetry.event_id,
                "grpc_code": exc.code().name if exc.code() else "UNKNOWN",
            })
            raise
        self.state.record(telemetry.asset_id, telemetry.event_id, telemetry.observed_at,
                          "submitted", diagnostic_id)
        logger.info("diagnostic_registered", extra={
            "asset_id": telemetry.asset_id, "event_id": telemetry.event_id,
            "diagnostic_id": diagnostic_id, "severity": result.severity,
        })

    def poll_once(self) -> None:
        watermark = self.state.watermark(self.settings.asset_id, self.settings.telemetry_from)
        query_from = max(
            self.settings.telemetry_from,
            watermark - timedelta(seconds=self.settings.replay_overlap_seconds),
        )
        latest_observed: datetime | None = None
        count = 0
        for telemetry in self.operational.stream_telemetry(query_from):
            count += 1
            if telemetry.asset_id == self.settings.asset_id:
                if latest_observed is None or telemetry.observed_at > latest_observed:
                    latest_observed = telemetry.observed_at
            self.process(telemetry)
            if self.stop_event.is_set():
                break
        if not self.stop_event.is_set() and latest_observed is not None:
            self.state.advance_watermark(self.settings.asset_id, latest_observed)
        logger.info("telemetry_poll_completed", extra={
            "asset_id": self.settings.asset_id, "records_received": count,
            "query_from": query_from.isoformat(),
            "watermark": latest_observed.isoformat() if latest_observed else watermark.isoformat(),
        })

    def run(self) -> None:
        logger.info("monitor_started", extra={
            "asset_id": self.settings.asset_id,
            "initial_from": self.settings.telemetry_from.isoformat(),
            "poll_interval_seconds": self.settings.poll_interval_seconds,
            "replay_overlap_seconds": self.settings.replay_overlap_seconds,
            "send_min_severity": self.settings.send_min_severity,
        })
        try:
            while not self.stop_event.is_set():
                try:
                    self.poll_once()
                except grpc.RpcError as exc:
                    logger.error("grpc_poll_failed", extra={
                        "grpc_code": exc.code().name if exc.code() else "UNKNOWN",
                        "details": exc.details(),
                    })
                if not self.stop_event.wait(self.settings.poll_interval_seconds):
                    continue
        finally:
            self.close()

    def stop(self) -> None:
        self.stop_event.set()

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self.operational.close()
        self.diagnostics.close()
        self.state.close()
