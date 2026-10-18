import logging
import signal
import sys

from integrity_analytics.application.monitor import IntegrityMonitor
from integrity_analytics.config import Settings
from integrity_analytics.logging_config import configure_logging


def main() -> int:
    configure_logging()
    logger = logging.getLogger("integrity_analytics")
    monitor: IntegrityMonitor | None = None
    try:
        settings = Settings.from_env()
        settings.validate_runtime()
        monitor = IntegrityMonitor(settings)
        signal.signal(signal.SIGINT, lambda _signum, _frame: monitor.stop())
        signal.signal(signal.SIGTERM, lambda _signum, _frame: monitor.stop())
        monitor.run()
        return 0
    except (ValueError, OSError) as exc:
        logger.error("configuration_or_runtime_error", extra={"reason": str(exc)})
        return 2
    except Exception:
        logger.exception("service_failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
