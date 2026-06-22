"""
Capa 3 — Ejecutor Determinista.

El cerebro (LLM) NUNCA toca el sistema directamente. Propone una acción estructurada;
el Auditor la aprueba; y SOLO entonces este ejecutor la realiza, dentro de límites.

(Fase 0: define el contrato. La ejecución real de acciones del sistema —abrir apps,
manejar archivos— se implementa en la Fase 4, siempre con confirmación y sandbox.)
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ActionType(Enum):
    OPEN_APP = "open_app"
    READ_FILE = "read_file"
    WRITE_FILE = "write_file"
    RUN_SCRIPT = "run_script"
    WEB_SEARCH = "web_search"
    SPEAK = "speak"


@dataclass
class Action:
    type: ActionType
    payload: dict
    requires_confirmation: bool = False


class Executor:
    """Ejecuta acciones aprobadas. En Fase 0 solo registra (dry-run)."""

    def __init__(self, dry_run: bool = True) -> None:
        self.dry_run = dry_run

    def execute(self, action: Action) -> str:
        if self.dry_run:
            return f"[dry-run] Acción '{action.type.value}' simulada: {action.payload}"
        raise NotImplementedError("La ejecución real llega en la Fase 4 (con sandbox y permisos).")
