from pathlib import Path
import grpc
from integrity_analytics.config import Settings


def create_channel(target: str, settings: Settings) -> grpc.Channel:
    if not settings.tls_enabled:
        return grpc.insecure_channel(target)
    root_certificates = Path(settings.root_cert_path).read_bytes()
    private_key = Path(settings.client_key_path).read_bytes() if settings.client_key_path else None
    certificate_chain = Path(settings.client_cert_path).read_bytes() if settings.client_cert_path else None
    credentials = grpc.ssl_channel_credentials(
        root_certificates=root_certificates,
        private_key=private_key,
        certificate_chain=certificate_chain,
    )
    return grpc.secure_channel(target, credentials)
