import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class EventState:
    def __init__(self, database_path: str) -> None:
        path = Path(database_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path, timeout=15)
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA foreign_keys=ON")
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS events ("
            "asset_id TEXT NOT NULL, event_id TEXT NOT NULL, observed_at TEXT NOT NULL, "
            "status TEXT NOT NULL, details TEXT, updated_at TEXT NOT NULL, "
            "PRIMARY KEY (asset_id, event_id))"
        )
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS checkpoints ("
            "asset_id TEXT PRIMARY KEY, watermark TEXT NOT NULL, updated_at TEXT NOT NULL)"
        )
        self.connection.commit()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _iso(value: datetime) -> str:
        if value.tzinfo is None:
            raise ValueError("observed_at deve incluir fuso horário")
        return value.astimezone(timezone.utc).isoformat()

    def status(self, asset_id: str, event_id: str) -> str | None:
        row = self.connection.execute(
            "SELECT status FROM events WHERE asset_id = ? AND event_id = ?",
            (asset_id, event_id),
        ).fetchone()
        return row[0] if row else None

    def record(self, asset_id: str, event_id: str, observed_at: datetime, status: str, details: str = "") -> None:
        self.connection.execute(
            "INSERT INTO events (asset_id, event_id, observed_at, status, details, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(asset_id, event_id) DO UPDATE SET "
            "observed_at=excluded.observed_at, status=excluded.status, "
            "details=excluded.details, updated_at=excluded.updated_at",
            (asset_id, event_id, self._iso(observed_at), status, details, self._now()),
        )
        self.connection.commit()

    def watermark(self, asset_id: str, initial: datetime) -> datetime:
        row = self.connection.execute(
            "SELECT watermark FROM checkpoints WHERE asset_id = ?", (asset_id,)
        ).fetchone()
        if not row:
            return initial.astimezone(timezone.utc)
        return datetime.fromisoformat(row[0]).astimezone(timezone.utc)

    def advance_watermark(self, asset_id: str, watermark: datetime) -> None:
        value = self._iso(watermark)
        self.connection.execute(
            "INSERT INTO checkpoints (asset_id, watermark, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(asset_id) DO UPDATE SET "
            "watermark=CASE WHEN excluded.watermark > checkpoints.watermark "
            "THEN excluded.watermark ELSE checkpoints.watermark END, "
            "updated_at=excluded.updated_at",
            (asset_id, value, self._now()),
        )
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()
