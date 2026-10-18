import json
import math
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class MeasurementRule:
    minimum: float
    maximum: float

    def __post_init__(self) -> None:
        if not math.isfinite(self.minimum) or not math.isfinite(self.maximum):
            raise ValueError("Os limites das medições devem ser finitos")
        if self.minimum >= self.maximum:
            raise ValueError("Cada regra exige minimum menor que maximum")


@dataclass(frozen=True)
class Settings:
    operational_target: str
    diagnostics_target: str
    asset_id: str
    fonte_id: int
    telemetry_from: datetime
    send_min_severity: int
    measurement_rules: dict[str, MeasurementRule]
    severity_thresholds: tuple[float, float, float]
    rpc_timeout_seconds: float
    stream_rpc_timeout_seconds: float
    poll_interval_seconds: float
    replay_overlap_seconds: float
    tls_enabled: bool
    root_cert_path: str | None
    client_cert_path: str | None
    client_key_path: str | None
    state_path: str

    @classmethod
    def from_env(cls) -> "Settings":
        try:
            raw_rules = json.loads(os.getenv("MEASUREMENT_RULES_JSON", "{}"))
        except json.JSONDecodeError as exc:
            raise ValueError("MEASUREMENT_RULES_JSON deve ser um JSON válido") from exc
        if not isinstance(raw_rules, dict):
            raise ValueError("MEASUREMENT_RULES_JSON deve ser um objeto JSON")
        rules: dict[str, MeasurementRule] = {}
        for name, rule in raw_rules.items():
            if not isinstance(name, str) or not name.strip() or not isinstance(rule, dict):
                raise ValueError("Cada regra deve ter um nome não vazio e um objeto de limites")
            try:
                rules[name] = MeasurementRule(float(rule["minimum"]), float(rule["maximum"]))
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(f"Regra inválida para a medição {name!r}") from exc
        try:
            thresholds = tuple(float(v.strip()) for v in os.getenv("SEVERITY_THRESHOLDS", "0.05,0.15,0.30").split(","))
        except ValueError as exc:
            raise ValueError("SEVERITY_THRESHOLDS deve conter três números") from exc
        if len(thresholds) != 3 or not all(math.isfinite(v) for v in thresholds) or not (0 <= thresholds[0] < thresholds[1] < thresholds[2]):
            raise ValueError("SEVERITY_THRESHOLDS deve conter três valores finitos e crescentes")
        telemetry_from_raw = os.getenv("TELEMETRY_FROM")
        if telemetry_from_raw:
            try:
                telemetry_from = datetime.fromisoformat(telemetry_from_raw.replace("Z", "+00:00"))
            except ValueError as exc:
                raise ValueError("TELEMETRY_FROM deve ser ISO 8601") from exc
            if telemetry_from.tzinfo is None:
                raise ValueError("TELEMETRY_FROM deve incluir fuso horário")
            telemetry_from = telemetry_from.astimezone(timezone.utc)
        else:
            telemetry_from = datetime.now(timezone.utc)
        fonte_raw = os.getenv("FONTE_ID", "")
        try:
            fonte_id = int(fonte_raw)
        except ValueError as exc:
            raise ValueError("FONTE_ID deve ser um inteiro confirmado no OPRS") from exc
        if fonte_id < 0:
            raise ValueError("FONTE_ID deve ser não negativo")
        send_min_severity = int(os.getenv("SEND_MIN_SEVERITY", "3"))
        if not 1 <= send_min_severity <= 5:
            raise ValueError("SEND_MIN_SEVERITY deve estar entre 1 e 5")
        rpc_timeout = float(os.getenv("RPC_TIMEOUT_SECONDS", "10"))
        stream_timeout = float(os.getenv("STREAM_RPC_TIMEOUT_SECONDS", "120"))
        poll_interval = float(os.getenv("POLL_INTERVAL_SECONDS", "15"))
        overlap = float(os.getenv("REPLAY_OVERLAP_SECONDS", "120"))
        for name, value in (("RPC_TIMEOUT_SECONDS", rpc_timeout), ("STREAM_RPC_TIMEOUT_SECONDS", stream_timeout), ("POLL_INTERVAL_SECONDS", poll_interval)):
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f"{name} deve ser positivo e finito")
        if not math.isfinite(overlap) or overlap < 0:
            raise ValueError("REPLAY_OVERLAP_SECONDS deve ser não negativo e finito")
        tls_enabled = os.getenv("GRPC_TLS_ENABLED", "false").lower() in {"1", "true", "yes"}
        root_cert = os.getenv("GRPC_ROOT_CERT_PATH") or None
        client_cert = os.getenv("GRPC_CLIENT_CERT_PATH") or None
        client_key = os.getenv("GRPC_CLIENT_KEY_PATH") or None
        return cls(
            operational_target=os.getenv("OPERATIONAL_GRPC_TARGET", "localhost:50051"),
            diagnostics_target=os.getenv("DIAGNOSTICS_GRPC_TARGET", "localhost:9090"),
            asset_id=os.getenv("ASSET_ID", ""), fonte_id=fonte_id,
            telemetry_from=telemetry_from, send_min_severity=send_min_severity,
            measurement_rules=rules, severity_thresholds=thresholds,
            rpc_timeout_seconds=rpc_timeout, stream_rpc_timeout_seconds=stream_timeout,
            poll_interval_seconds=poll_interval, replay_overlap_seconds=overlap,
            tls_enabled=tls_enabled, root_cert_path=root_cert,
            client_cert_path=client_cert, client_key_path=client_key,
            state_path=os.getenv("STATE_DB_PATH", "./data/analytics-state.sqlite3"),
        )

    def validate_runtime(self) -> None:
        if not self.asset_id.strip():
            raise ValueError("ASSET_ID é obrigatório")
        if not self.measurement_rules:
            raise ValueError("Configure MEASUREMENT_RULES_JSON com limites validados")
        if self.tls_enabled and not self.root_cert_path:
            raise ValueError("GRPC_ROOT_CERT_PATH é obrigatório quando TLS está habilitado")
        if bool(self.client_cert_path) != bool(self.client_key_path):
            raise ValueError("GRPC_CLIENT_CERT_PATH e GRPC_CLIENT_KEY_PATH devem ser definidos juntos")
        for path in (self.root_cert_path, self.client_cert_path, self.client_key_path):
            if path and not Path(path).is_file():
                raise ValueError(f"Arquivo de certificado não encontrado: {path}")
