"""Persistência local de lotes de jogos gerados (SQLite, sem dependência externa)."""
from __future__ import annotations

from contextlib import closing
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
from typing import Any, Dict, List, Optional
import uuid


class GameStore:
    def __init__(self, database_path: Optional[str | Path] = None):
        default_path = Path(__file__).resolve().parent / "data" / "lottoia.sqlite3"
        self.database_path = Path(database_path or os.getenv("LOTTO_DB_PATH", default_path))
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=15)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 15000")
        return connection

    def initialize(self) -> None:
        with closing(self._connect()) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS generated_batches (
                    id TEXT PRIMARY KEY,
                    owner TEXT NOT NULL,
                    name TEXT NOT NULL,
                    lottery TEXT NOT NULL,
                    method TEXT NOT NULL,
                    number_count INTEGER NOT NULL,
                    game_count INTEGER NOT NULL,
                    source TEXT NOT NULL,
                    reference_draw INTEGER,
                    games_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_generated_batches_owner_created "
                "ON generated_batches(owner, created_at DESC)"
            )
            connection.commit()

    @staticmethod
    def _decode(row: sqlite3.Row) -> Dict[str, Any]:
        result = dict(row)
        result["games"] = json.loads(result.pop("games_json"))
        return result

    def create_batch(
        self,
        *,
        owner: str,
        name: str,
        lottery: str,
        method: str,
        number_count: int,
        source: str,
        reference_draw: Optional[int],
        games: List[List[int]],
    ) -> Dict[str, Any]:
        batch = {
            "id": uuid.uuid4().hex,
            "owner": owner,
            "name": name,
            "lottery": lottery,
            "method": method,
            "number_count": number_count,
            "game_count": len(games),
            "source": source,
            "reference_draw": reference_draw,
            "games": games,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        with closing(self._connect()) as connection:
            connection.execute(
                """
                INSERT INTO generated_batches (
                    id, owner, name, lottery, method, number_count, game_count,
                    source, reference_draw, games_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    batch["id"], batch["owner"], batch["name"], batch["lottery"],
                    batch["method"], batch["number_count"], batch["game_count"],
                    batch["source"], batch["reference_draw"],
                    json.dumps(games, separators=(",", ":")), batch["created_at"],
                ),
            )
            connection.commit()
        return batch

    def get_batch(self, batch_id: str, owner: str) -> Optional[Dict[str, Any]]:
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT * FROM generated_batches WHERE id = ? AND owner = ?",
                (batch_id, owner),
            ).fetchone()
        return self._decode(row) if row else None

    def list_batches(self, owner: str, limit: int = 100) -> List[Dict[str, Any]]:
        limit = max(1, min(int(limit), 100))
        with closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT * FROM generated_batches WHERE owner = ? "
                "ORDER BY created_at DESC, id DESC LIMIT ?",
                (owner, limit),
            ).fetchall()
        return [self._decode(row) for row in rows]


_DEFAULT_DB_PATH = os.getenv("LOTTO_DB_PATH")
GAME_STORE = GameStore(_DEFAULT_DB_PATH)
