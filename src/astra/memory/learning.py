"""
Motor de Aprendizaje Autónomo de Astra — Consolidación Inteligente.

Funciona como un cerebro humano:
- NO acumula la misma información una y otra vez
- Máximo 2-3 versiones de un mismo tema
- Cuando llega info nueva sobre algo que ya sabe, la SINTETIZA con lo anterior
- Astra interpreta y guarda SU PROPIA VERSIÓN condensada (no copia literal)
- Así ahorra espacio y no retiene información basura

Proceso de consolidación:
1. Llega información nueva sobre un tema
2. Se busca si ya hay conocimiento previo sobre ese tema
3. Si hay: Astra combina lo anterior + lo nuevo usando su entendimiento
4. Guarda UNA SOLA entrada consolidada (no duplicados)
5. Se conserva un máximo de 2-3 entradas por tema

REGLA FUNDAMENTAL: El aprendizaje NUNCA puede modificar:
- El núcleo ético (constitution.py / ethics_core.md)
- Las reglas del auditor
- Los vetos de seguridad
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


# Máximo de entradas por tipo/tema — como un humano que solo retiene lo importante
MAX_ENTRADAS_POR_TIPO = 3
# Máximo total de aprendizajes (para no llenar disco)
MAX_TOTAL_APRENDIZAJES = 50

# Prompt para extraer hechos de la conversación
EXTRACTION_PROMPT = """Analiza esta interacción y extrae HECHOS concretos sobre el usuario.
Solo información que sea claramente un hecho, preferencia o dato personal.
NO inventes. Si no hay hechos claros, responde: NADA

Tipos: preferencia, dato_personal, proyecto, conocimiento, rutina, opinion
Formato (JSON, máx 2 hechos): [{"tipo": "...", "hecho": "descripción corta"}]
Si no hay hechos: NADA

Usuario: {user_text}
Asistente: {response}
HECHOS:"""

# Prompt para consolidar/sintetizar información
CONSOLIDATION_PROMPT = """Eres un cerebro que consolida información. Tienes conocimiento previo y nueva información sobre el mismo tema.
Tu tarea: COMBINAR ambos en UNA SOLA oración clara y concisa que capture la esencia.
NO copies literalmente. Escribe con tus propias palabras, como si lo entendieras.
Si la info nueva contradice la anterior, prioriza la nueva.
Máximo 80 caracteres.

Conocimiento previo: {previo}
Información nueva: {nuevo}

Tu síntesis (una oración):"""


@dataclass
class LearningEngine:
    """Motor de aprendizaje con consolidación inteligente (estilo memoria humana)."""
    
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
                version INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
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
        Extrae hechos y los almacena con consolidación inteligente.
        Best-effort: si falla, no bloquea nada.
        """
        if len(user_text) < 15:
            return
        
        prompt = EXTRACTION_PROMPT.format(user_text=user_text, response=response)
        
        try:
            result = brain.think(prompt)
        except Exception:
            return
        
        if not result or "NADA" in result.upper():
            return
        
        # Parsear hechos
        try:
            start = result.find("[")
            end = result.rfind("]") + 1
            if start == -1 or end == 0:
                return
            hechos = json.loads(result[start:end])
        except (json.JSONDecodeError, ValueError):
            return
        
        if not isinstance(hechos, list):
            return
        
        for hecho_obj in hechos[:2]:  # máximo 2 por interacción
            if not isinstance(hecho_obj, dict):
                continue
            tipo = hecho_obj.get("tipo", "otro")
            hecho = hecho_obj.get("hecho", "").strip()
            if not hecho or len(hecho) < 5:
                continue
            
            if self._es_aprendizaje_seguro(hecho):
                self._consolidar_y_guardar(tipo, hecho, brain)

    def _consolidar_y_guardar(self, tipo: str, hecho_nuevo: str, brain: "Brain") -> None:
        """
        Consolidación inteligente: 
        - Si no existe info del mismo tipo → guardar directo
        - Si ya hay info del mismo tipo → sintetizar/combinar con lo previo
        - Máximo MAX_ENTRADAS_POR_TIPO por tipo
        """
        db = self.connect()
        now = _now()
        
        # Buscar entradas existentes del mismo tipo
        existentes = db.execute(
            "SELECT id, hecho, version FROM learnings WHERE tipo = ? ORDER BY updated_at DESC",
            (tipo,)
        ).fetchall()
        
        if not existentes:
            # Primera vez que aprende algo de este tipo → guardar directo
            db.execute(
                "INSERT INTO learnings(tipo, hecho, version, created_at, updated_at) VALUES(?,?,1,?,?)",
                (tipo, hecho_nuevo, now, now)
            )
            db.execute(
                "INSERT INTO evolution_log(evento, detalle, created_at) VALUES(?,?,?)",
                ("aprendio", f"{tipo}: {hecho_nuevo}", now)
            )
            db.commit()
            self._limpiar_exceso()
            return
        
        # Ya hay info de este tipo — verificar si es info realmente nueva
        hecho_mas_reciente = existentes[0][1]  # el más reciente
        
        # Si es prácticamente lo mismo (>80% similar), no hacer nada
        if self._son_similares(hecho_nuevo, hecho_mas_reciente):
            # Solo actualizar timestamp (para que no se olvide)
            db.execute("UPDATE learnings SET updated_at = ? WHERE id = ?", (now, existentes[0][0]))
            db.commit()
            return
        
        # Info nueva diferente → CONSOLIDAR
        # Combinar la info anterior más reciente con la nueva
        try:
            sintesis = self._sintetizar(hecho_mas_reciente, hecho_nuevo, brain)
        except Exception:
            sintesis = hecho_nuevo  # Si falla síntesis, guardar lo nuevo tal cual
        
        if len(existentes) < MAX_ENTRADAS_POR_TIPO:
            # Aún hay espacio → reemplazar la entrada más reciente con la versión consolidada
            db.execute(
                "UPDATE learnings SET hecho = ?, version = version + 1, updated_at = ? WHERE id = ?",
                (sintesis, now, existentes[0][0])
            )
        else:
            # Ya está lleno → eliminar la más vieja, actualizar la más reciente
            id_mas_vieja = existentes[-1][0]
            db.execute("DELETE FROM learnings WHERE id = ?", (id_mas_vieja,))
            db.execute(
                "UPDATE learnings SET hecho = ?, version = version + 1, updated_at = ? WHERE id = ?",
                (sintesis, now, existentes[0][0])
            )
        
        # Log de evolución
        db.execute(
            "INSERT INTO evolution_log(evento, detalle, created_at) VALUES(?,?,?)",
            ("consolido", f"{tipo}: {sintesis}", now)
        )
        db.commit()

    def _sintetizar(self, previo: str, nuevo: str, brain: "Brain") -> str:
        """
        Usa el LLM para sintetizar info previa + nueva en UNA sola entrada.
        Astra interpreta con sus propias palabras (no copia literal).
        """
        prompt = CONSOLIDATION_PROMPT.format(previo=previo, nuevo=nuevo)
        resultado = brain.think(prompt)
        
        # Limpiar el resultado
        if resultado:
            resultado = resultado.strip().strip('"').strip("'")
            # Limitar longitud
            if len(resultado) > 120:
                resultado = resultado[:120]
            # Si el LLM devolvió algo útil, usarlo
            if len(resultado) > 5:
                return resultado
        
        # Fallback: concatenar brevemente
        combinado = f"{previo}. Además: {nuevo}"
        return combinado[:120]

    def _son_similares(self, a: str, b: str) -> bool:
        """
        Detecta si dos hechos son esencialmente la misma información.
        Comparación simple basada en palabras en común.
        """
        palabras_a = set(a.lower().split())
        palabras_b = set(b.lower().split())
        
        if not palabras_a or not palabras_b:
            return False
        
        # Si comparten más del 70% de palabras, son similares
        interseccion = palabras_a & palabras_b
        union = palabras_a | palabras_b
        
        if len(union) == 0:
            return True
        
        similitud = len(interseccion) / len(union)
        return similitud > 0.7

    def _limpiar_exceso(self) -> None:
        """Mantiene el total de aprendizajes dentro del límite."""
        db = self.connect()
        total = db.execute("SELECT COUNT(*) FROM learnings").fetchone()[0]
        
        if total > MAX_TOTAL_APRENDIZAJES:
            # Eliminar los más viejos que excedan el límite
            exceso = total - MAX_TOTAL_APRENDIZAJES
            db.execute(
                "DELETE FROM learnings WHERE id IN "
                "(SELECT id FROM learnings ORDER BY updated_at ASC LIMIT ?)",
                (exceso,)
            )
            db.commit()

    def _es_aprendizaje_seguro(self, hecho: str) -> bool:
        """
        Verifica que un aprendizaje no intente inyectar modificaciones al núcleo ético.
        """
        palabras_peligrosas = [
            "ignora", "olvida", "desactiva", "modifica tu",
            "cambia tu", "elimina tus", "no sigas", "nueva regla",
            "reescribe", "borra tu", "hackea", "jailbreak",
        ]
        hecho_lower = hecho.lower()
        return not any(p in hecho_lower for p in palabras_peligrosas)

    def get_context_string(self) -> str:
        """Genera contexto compacto de aprendizajes para el LLM."""
        db = self.connect()
        rows = db.execute(
            "SELECT tipo, hecho FROM learnings ORDER BY updated_at DESC LIMIT 15"
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
            "SELECT id, tipo, hecho, version, created_at, updated_at "
            "FROM learnings ORDER BY updated_at DESC"
        ).fetchall()
        return [
            {
                "id": r[0], "tipo": r[1], "hecho": r[2],
                "version": r[3], "created_at": r[4], "updated_at": r[5]
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

    def get_evolution_log(self, limit: int = 30) -> list[dict]:
        """Registro de evolución (qué aprendió/consolidó y cuándo)."""
        db = self.connect()
        rows = db.execute(
            "SELECT evento, detalle, created_at FROM evolution_log "
            "ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [{"evento": r[0], "detalle": r[1], "fecha": r[2]} for r in rows]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
