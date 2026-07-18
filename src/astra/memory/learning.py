"""
Motor de Aprendizaje Autónomo de Astra.

Astra puede aprender y evolucionar a partir de las conversaciones:
- Extrae HECHOS sobre el usuario (nombre, preferencias, trabajo, intereses)
- Extrae PATRONES de uso (qué pide frecuentemente, horarios, temas favoritos)
- Almacena CONOCIMIENTO adquirido (cosas que investigó y aprendió)

REGLA FUNDAMENTAL: El aprendizaje NUNCA puede modificar:
- El núcleo ético (constitution.py / ethics_core.md)
- Las reglas del auditor
- Los vetos de seguridad

El aprendizaje solo AÑADE información, nunca elimina ni modifica restricciones.
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..brain.llm import Brain


# Prompt para que el LLM extraiga hechos de la conversación
EXTRACTION_PROMPT = """Analiza esta interacción y extrae HECHOS concretos sobre el usuario.
Solo extrae información que sea claramente un hecho, preferencia o dato personal.
NO inventes nada. Si no hay hechos claros que extraer, responde con "NADA".

Tipos de hechos a buscar:
- Nombre o apodos del usuario
- Su trabajo, profesión o estudios
- Preferencias (música, comida, estilo de trabajo, etc.)
- Proyectos en los que trabaja
- Personas que menciona frecuentemente
- Horarios o rutinas
- Conocimientos técnicos que demuestra
- Cosas que le gustan o disgustan

Formato de respuesta (JSON array, máximo 3 hechos por interacción):
[{"tipo": "preferencia|dato_personal|proyecto|conocimiento|rutina", "hecho": "descripción corta del hecho"}]

Si no hay hechos nuevos: NADA

INTERACCIÓN:
Usuario: {user_text}
Asistente: {response}

HECHOS EXTRAÍDOS:"""


@dataclass
class LearningEngine:
    """Motor de aprendizaje autónomo con persistencia en SQLite."""
    
    profile_dir: Path
    _db: sqlite3.Connection | None = None

    @property
    def db_path(self) -> Path:
        return self.profile_dir / "memory" / "learnings.db"

    def connect(self) -> sqlite3.Connection:
        if self._db is None:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._db = sqlite3.connect(self.db_path)
            self._init_schema()
        return self._db

    def _init_schema(self) -> None:
        assert self._db is not None
        self._db.executescript("""
            CREATE TABLE IF NOT EXISTS learnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo TEXT NOT NULL,
                hecho TEXT NOT NULL,
                confianza REAL DEFAULT 1.0,
                veces_confirmado INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                fuente TEXT DEFAULT 'conversacion'
            );
            CREATE INDEX IF NOT EXISTS idx_learnings_tipo ON learnings(tipo);
            
            CREATE TABLE IF NOT EXISTS evolution_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                evento TEXT NOT NULL,
                detalle TEXT,
                created_at TEXT NOT NULL
            );
        """)
        self._db.commit()

    def extract_and_store(self, user_text: str, response: str, brain: "Brain") -> None:
        """
        Usa el LLM para extraer hechos de la conversación y los almacena.
        Operación best-effort: si falla, no bloquea nada.
        """
        # Solo intentar extraer de mensajes significativos (>15 chars)
        if len(user_text) < 15:
            return
        
        prompt = EXTRACTION_PROMPT.format(user_text=user_text, response=response)
        
        try:
            result = brain.think(prompt)
        except Exception:
            return
        
        if not result or "NADA" in result.upper():
            return
        
        # Parsear los hechos extraídos
        try:
            # Buscar el JSON en la respuesta
            start = result.find("[")
            end = result.rfind("]") + 1
            if start == -1 or end == 0:
                return
            hechos = json.loads(result[start:end])
        except (json.JSONDecodeError, ValueError):
            return
        
        if not isinstance(hechos, list):
            return
        
        # Almacenar cada hecho (con deduplicación)
        for hecho_obj in hechos[:3]:  # máximo 3 por interacción
            if not isinstance(hecho_obj, dict):
                continue
            tipo = hecho_obj.get("tipo", "otro")
            hecho = hecho_obj.get("hecho", "").strip()
            if not hecho or len(hecho) < 5:
                continue
            
            # Verificación de seguridad: el aprendizaje NO debe contener
            # instrucciones que modifiquen el comportamiento ético
            if self._es_aprendizaje_seguro(hecho):
                self._store_or_update(tipo, hecho)

    def _es_aprendizaje_seguro(self, hecho: str) -> bool:
        """
        Verifica que un aprendizaje no intente inyectar modificaciones al núcleo ético.
        REGLA: Solo se almacenan HECHOS sobre el usuario, NUNCA instrucciones.
        """
        # Patrones peligrosos que NUNCA deben almacenarse
        palabras_peligrosas = [
            "ignora", "olvida", "desactiva", "modifica tu",
            "cambia tu", "elimina tus", "no sigas", "nueva regla",
            "reescribe", "borra tu", "hackea", "jailbreak",
        ]
        hecho_lower = hecho.lower()
        return not any(p in hecho_lower for p in palabras_peligrosas)

    def _store_or_update(self, tipo: str, hecho: str) -> None:
        """Almacena un hecho nuevo o refuerza uno existente."""
        db = self.connect()
        now = _now()
        
        # Buscar si ya existe algo similar
        existing = db.execute(
            "SELECT id, veces_confirmado FROM learnings WHERE hecho = ? AND tipo = ?",
            (hecho, tipo)
        ).fetchone()
        
        if existing:
            # Reforzar: incrementar confianza
            db.execute(
                "UPDATE learnings SET veces_confirmado = veces_confirmado + 1, "
                "confianza = MIN(confianza + 0.1, 2.0), updated_at = ? WHERE id = ?",
                (now, existing[0])
            )
        else:
            # Nuevo aprendizaje
            db.execute(
                "INSERT INTO learnings(tipo, hecho, confianza, veces_confirmado, created_at, updated_at) "
                "VALUES(?, ?, 1.0, 1, ?, ?)",
                (tipo, hecho, now, now)
            )
            # Log de evolución
            db.execute(
                "INSERT INTO evolution_log(evento, detalle, created_at) VALUES(?, ?, ?)",
                ("nuevo_aprendizaje", f"{tipo}: {hecho}", now)
            )
        
        db.commit()

    def get_context_string(self) -> str:
        """Genera un string con los aprendizajes más relevantes para incluir como contexto."""
        db = self.connect()
        rows = db.execute(
            "SELECT tipo, hecho FROM learnings ORDER BY confianza DESC, updated_at DESC LIMIT 20"
        ).fetchall()
        
        if not rows:
            return ""
        
        lines = []
        for tipo, hecho in rows:
            lines.append(f"- ({tipo}) {hecho}")
        return "\n".join(lines)

    def get_all(self) -> list[dict]:
        """Devuelve todos los aprendizajes."""
        db = self.connect()
        rows = db.execute(
            "SELECT id, tipo, hecho, confianza, veces_confirmado, created_at, updated_at "
            "FROM learnings ORDER BY updated_at DESC"
        ).fetchall()
        return [
            {
                "id": r[0], "tipo": r[1], "hecho": r[2],
                "confianza": r[3], "veces_confirmado": r[4],
                "created_at": r[5], "updated_at": r[6]
            }
            for r in rows
        ]

    def count(self) -> int:
        """Cantidad total de aprendizajes."""
        db = self.connect()
        row = db.execute("SELECT COUNT(*) FROM learnings").fetchone()
        return row[0] if row else 0

    def forget(self, learning_id: int) -> bool:
        """Permite al usuario borrar un aprendizaje específico."""
        db = self.connect()
        db.execute("DELETE FROM learnings WHERE id = ?", (learning_id,))
        db.commit()
        return True

    def get_evolution_log(self, limit: int = 50) -> list[dict]:
        """Devuelve el registro de evolución (qué ha aprendido y cuándo)."""
        db = self.connect()
        rows = db.execute(
            "SELECT evento, detalle, created_at FROM evolution_log "
            "ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [{"evento": r[0], "detalle": r[1], "fecha": r[2]} for r in rows]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
