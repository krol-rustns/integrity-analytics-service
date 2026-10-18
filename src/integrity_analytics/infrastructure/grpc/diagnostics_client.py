from datetime import datetime, timezone
from google.protobuf.timestamp_pb2 import Timestamp
from integrity_analytics.config import Settings
from integrity_analytics.generated import diagnostico_pb2, diagnostico_pb2_grpc
from integrity_analytics.infrastructure.grpc.channel import create_channel


class DiagnosticsClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.channel = create_channel(settings.diagnostics_target, settings)
        self.stub = diagnostico_pb2_grpc.DiagnosticoServiceStub(self.channel)

    def register(self, description: str, severity: int) -> str:
        created_at = Timestamp()
        created_at.FromDatetime(datetime.now(timezone.utc))
        request = diagnostico_pb2.DiagnosticoRequest(
            fonte_id=self.settings.fonte_id,
            descricao=description,
            dt_criacao=created_at,
            severidade=severity,
        )
        response = self.stub.RegistrarDiagnostico(
            request, timeout=self.settings.rpc_timeout_seconds
        )
        return response.id

    def close(self) -> None:
        self.channel.close()
