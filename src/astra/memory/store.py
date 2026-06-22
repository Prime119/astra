"""
Capa 4 — Memoria de Astra.

Tres niveles (F.R.I.D.A.Y. / Zane / 2B):
- Volátil      : el contexto de la conversación actual (en RAM, no se guarda).
- Corto plazo  : estado, tareas, preferencias -> SQLite en el PERFIL.
- Episódica    : recuerdos importantes con "peso" -> base vectorial (Fase 2).

Importante: TODO se escribe en `astra-perfil/`. La base es de solo lectura, así que
borrar el perfil reinicia a Astra "como nueva" y otro usuario puede tener el suyo.
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class Memory:
    profile_dir: Path
    _db: sqlite3.Connection | None = None

    @property
    def db_path(self) -> Path:
        return self.profile_dir / "memory" / "astra.db"

    def connect(self) -> sqlite3.Connection:
        if self._db is None:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._db = sqlite3.connect(self.db_path)
            self._init_schema()
        return self._db

    def _init_schema(self) -> None:
        assert self._db is not None
        self._db.executescript(
            """
            CREATE TABLE IF NOT EXISTS short_term (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE,
                value TEXT,
                updated_at TEXT
            );
            CREATE TABLE IF NOT EXISTS episodic (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT,
                content TEXT,
                emotional_weight REAL DEFAULT 0.0,
                created_at TEXT
            );
            """
        )
        self._db.commit()

    # --- Corto plazo (clave/valor) ---
    def remember(self, key: str, value: object) -> None:
        db = self.connect()
        db.execute(
            "INSERT INTO short_term(key, value, updated_at) VALUES(?,?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
            (key, json.dumps(value, ensure_ascii=False), _now()),
        )
        db.commit()

    def recall(self, key: str, default: object = None) -> object:
        db = self.connect()
        row = db.execute("SELECT value FROM short_term WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else default

    # --- Episódica (recuerdos con peso) ---
    def log_episode(self, category: str, content: str, emotional_weight: float = 0.0) -> None:
        db = self.connect()
        db.execute(
            "INSERT INTO episodic(category, content, emotional_weight, created_at) VALUES(?,?,?,?)",
            (category, content, emotional_weight, _now()),
        )
        db.commit()

    def reset(self) -> None:
        """Reinicio limpio: olvida todo (borra la BD del perfil)."""
        if self._db is not None:
            self._db.close()
            self._db = None
        if self.db_path.exists():
            self.db_path.unlink()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
