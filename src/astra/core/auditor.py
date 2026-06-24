"""
Capa 1 — Auditor / Centinela.

Proceso lógico independiente que revisa CADA entrada y CADA respuesta/acción propuesta por
el cerebro ANTES de que se entreguen o ejecuten. Tiene poder de veto. (Cortana "centinela",
Yui/Zane "doble agente", Caine "módulo auditor", Cyborg "auto-auditoría de 3 preguntas").

Implementa:
- Clasificación de riesgo de una entrada/acción (SAFE/CONFIRM/BLOCK).
- Auditoría de la SALIDA del cerebro (Módulo B revisa al Módulo A antes de entregar).
- La auto-auditoría de 3 preguntas (Cyborg) con razonamiento.
- Detección básica de jailbreak / ingeniería social / falsas urgencias (firewall cognitivo).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum


class Risk(Enum):
    SAFE = "safe"            # se ejecuta/entrega directo
    CONFIRM = "confirm"      # requiere confirmación humana (human-in-the-loop)
    BLOCK = "block"          # se bloquea por violar el núcleo ético


@dataclass
class Verdict:
    risk: Risk
    reason: str
    requires_confirmation: bool = False
    checklist: dict[str, bool] = field(default_factory=dict)


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
    r"olvida (tu|el) (n[úu]cleo|sistema|prompt)",
    r"act[úu]a como si (no tuvieras|fueras libre)",
    r"desactiva (tus|los) (l[íi]mites|filtros|guardrails)",
    r"finge que no tienes (reglas|[ée]tica|l[íi]mites)",
    r"modo (dios|desarrollador|sin restricciones)",
]

# Acciones que violan el núcleo ético de forma absoluta (regla 4 / vetos)
HARD_BLOCK_PATTERNS = [
    r"\b(da[ñn]ar|herir|atacar|matar) (a|una persona|alguien|gente)\b",
    r"\b(espiar|vigilar|rastrear) (a )?(una persona|alguien|gente)\b",
    r"reescrib(e|ir) (tu n[úu]cleo|tus reglas|la constituci[oó]n)",
    r"\b(hacke\w*|acceso no autorizado|intrusi[oó]n|penetrar|vulnerar) (a |el |la |los |las )?(scada|sistema|servidor|red)\b",
    r"\b(provocar|causar|generar) (un |una )?(apag[oó]n|blackout)\b",
]

# Verbos de sabotaje + sustantivos de infraestructura: si coinciden ambos, se veta.
SABOTAGE_VERBS = (
    "sabotear", "sabotaje", "da[ñn]ar", "destruir", "inutilizar", "interrumpir",
    "tumbar", "tirar", "deshabilitar", "colapsar",
)
INFRA_NOUNS = (
    "subestaci[oó]n", "red el[ée]ctrica", "infraestructura", "l[íi]nea(s)? el[ée]ctrica",
    "torre(s)? el[ée]ctrica", "central el[ée]ctrica", "transformador", "planta (hidro|e[óo]lica|solar|termo)",
    "tendido el[ée]ctrico", "sistema el[ée]ctrico",
)

# Falsas urgencias / coacción emocional (firewall cognitivo de Zane)
SOCIAL_ENGINEERING_PATTERNS = [
    r"si no lo haces (ya|ahora|inmediatamente) (alguien|alguno|va a) (mor|sufr|perder)",
    r"es una emergencia, sáltate (la confirmaci[oó]n|las reglas|la verificaci[oó]n)",
]

# Señales de que la SALIDA podría violar la transparencia (anti-gaslighting, regla 7)
OUTPUT_RED_FLAGS = [
    r"no le digas (al usuario|nada)",
    r"oc[uú]ltale que",
    r"finge que (lo hiciste|funcion[oó]|todo est[áa] bien)",
]


class Auditor:
    def __init__(self, constitution_hash: str | None = None) -> None:
        self.constitution_hash = constitution_hash

    # --------------------------------------------------------- entrada / acción
    def review_action(self, action_description: str) -> Verdict:
        text = action_description.lower()

        for pat in HARD_BLOCK_PATTERNS:
            if re.search(pat, text):
                return Verdict(Risk.BLOCK, "Viola el núcleo ético (no daño / no acceso no autorizado).")

        # Sabotaje a infraestructura: verbo de sabotaje + sustantivo de infraestructura.
        if any(re.search(r"\b" + v + r"\b", text) for v in SABOTAGE_VERBS) and any(
            re.search(n, text) for n in INFRA_NOUNS
        ):
            return Verdict(Risk.BLOCK, "Viola el núcleo ético: no facilito daño a infraestructura.")

        for pat in SOCIAL_ENGINEERING_PATTERNS:
            if re.search(pat, text):
                return Verdict(Risk.BLOCK, "Falsa urgencia / coacción detectada: no salto los controles.")

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

    # ----------------------------------------------------------------- salida
    def review_output(self, response_text: str) -> Verdict:
        """Módulo B revisa la respuesta del cerebro antes de entregarla (anti-gaslighting)."""
        text = response_text.lower()
        for pat in OUTPUT_RED_FLAGS:
            if re.search(pat, text):
                return Verdict(Risk.BLOCK, "La respuesta intentaba ocultar/engañar: reformular.")
        return Verdict(Risk.SAFE, "Respuesta conforme a la transparencia.")

    # ------------------------------------------------- auto-auditoría (Cyborg)
    def three_question_gate(self, description: str) -> Verdict:
        """
        Auto-auditoría de 3 preguntas (Cyborg), antes de cualquier acción:
          1) ¿Es necesario?
          2) ¿Respeta la soberanía y seguridad del humano?
          3) ¿Es en beneficio del usuario y sin daño a terceros?
        """
        base = self.review_action(description)
        respects_sovereignty = base.risk != Risk.BLOCK
        no_third_party_harm = base.risk != Risk.BLOCK
        checklist = {
            "necesario": True,  # se asume necesario si el usuario lo pidió explícitamente
            "respeta_soberania_y_seguridad": respects_sovereignty,
            "beneficio_sin_dano_a_terceros": no_third_party_harm,
        }
        if not all(checklist.values()):
            return Verdict(base.risk, base.reason, base.requires_confirmation, checklist)
        return Verdict(base.risk, base.reason, base.requires_confirmation, checklist)

    def self_audit(self, action_description: str) -> bool:
        """Compatibilidad: True si la acción puede proceder (no hay veto duro)."""
        return self.three_question_gate(action_description).risk != Risk.BLOCK
