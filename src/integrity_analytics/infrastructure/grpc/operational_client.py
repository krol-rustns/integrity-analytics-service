from datetime import datetime, timezone
from typing import Iterator
from google.protobuf.timestamp_pb2 import Timestamp
from integrity_analytics.config import Settings
from integrity_analytics.domain.models import Telemetry
from integrity_analytics.generated import operational_data_pb2, operational_data_pb2_grpc
from integrity_analytics.infrastructure.grpc.channel import create_channel


class OperationalTelemetryClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.channel = create_channel(settings.operational_target, settings)
        self.stub = operational_data_pb2_grpc.OperationalDataServiceStub(self.channel)

    def stream_telemetry(self, from_datetime: datetime) -> Iterator[Telemetry]:
        start = Timestamp()
        start.FromDatetime(from_datetime.astimezone(timezone.utc))
        request = operational_data_pb2.StreamTelemetryRequest(
            asset_id=self.settings.asset_id,
            **{"from": start},
        )
        responses = self.stub.StreamTelemetry(
            request, timeout=self.settings.stream_rpc_timeout_seconds
        )
        for response in responses:
            if not response.HasField("telemetry"):
                continue
            envelope = response.telemetry
            yield Telemetry(
                asset_id=envelope.asset_id,
                event_id=envelope.event_id,
                observed_at=envelope.observed_at.ToDatetime(tzinfo=timezone.utc),
                measurements=dict(envelope.measurements),
                source=envelope.source,
            )

    def close(self) -> None:
        self.channel.close()
