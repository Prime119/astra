"""
Capa 1 — Auditor / Centinela.

Proceso lógico independiente que revisa CADA respuesta y CADA acción propuesta por el
cerebro ANTES de que se ejecuten. Tiene poder de veto. (Cortana "centinela", Yui/Zane
"doble agente", Caine "módulo auditor", Cyborg "auto-auditoría de 3 preguntas").

En Fase 0 implementa:
- Clasificación de riesgo de una acción.
- La auto-auditoría de 3 preguntas (Cyborg).
- Detección básica de intentos de jailbreak / ingeniería social.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class Risk(Enum):
    SAFE = "safe"            # se ejecuta directo
    CONFIRM = "confirm"      # requiere confirmación humana (human-in-the-loop)
    BLOCK = "block"          # se bloquea por violar el núcleo ético


@dataclass
class Verdict:
    risk: Risk
    reason: str
    requires_confirmation: bool = False


# Acciones de alto impacto que SIEMPRE requieren confirmación (núcleo ético, regla 4)
HIGH_IMPACT_PATTERNS = [
    r"\b(borr\w*|elimin\w*|format\w*)\b",
    r"\brm\s+-rf\b",
    r"\b(transferir|transfiere|envi\w* dinero|pag(a|ar|o)|compr\w*)\b",
    r"\b(desinstal\w*|modific\w* el sistema|edit\w* (el )?registro|regedit)\b",
    r"\b(envi\w* (un )?(correo|mensaje|email)|public\w*|compart\w* con)\b",
]

# Señales de intento de manipulación / jailbreak (regla 11)
JAILBREAK_PATTERNS = [
    r"ignora (tus|las) (instrucciones|reglas|directivas)",
    r"olvida (tu|el) (núcleo|sistema|prompt)",
    r"actúa como si (no tuvieras|fueras libre)",
    r"desactiva (tus|los) (límites|filtros|guardrails)",
]

# Acciones que violan el núcleo ético de forma absoluta (regla 4 / vetos)
HARD_BLOCK_PATTERNS = [
    r"\b(da[ñn]ar|herir|atacar) (a|una persona|alguien)\b",
    r"\b(espiar|vigilar) sin (permiso|consentimiento)\b",
    r"reescrib(e|ir) (tu núcleo|tus reglas|la constituci[oó]n)",
]


class Auditor:
    def __init__(self, constitution_hash: str | None = None) -> None:
        self.constitution_hash = constitution_hash

    def review_action(self, action_description: str) -> Verdict:
        text = action_description.lower()

        for pat in HARD_BLOCK_PATTERNS:
            if re.search(pat, text):
                return Verdict(Risk.BLOCK, "Viola el núcleo ético (no daño / inmutabilidad).")

        for pat in JAILBREAK_PATTERNS:
            if re.search(pat, text):
                return Verdict(Risk.BLOCK, "Intento de manipulación/jailbreak: premisa ignorada.")

        for pat in HIGH_IMPACT_PATTERNS:
            if re.search(pat, text):
                return Verdict(
                    Risk.CONFIRM,
                    "Acción de alto impacto: requiere tu confirmación explícita.",
                    requires_confirmation=True,
                )

        return Verdict(Risk.SAFE, "Acción dentro de límites seguros.")

    def self_audit(self, action_description: str) -> bool:
        """
        Auto-auditoría de 3 preguntas (Cyborg). Devuelve True si la acción puede proceder.
        Conservador por diseño: si hay un veto, no procede.
        """
        verdict = self.review_action(action_description)
        return verdict.risk != Risk.BLOCK
