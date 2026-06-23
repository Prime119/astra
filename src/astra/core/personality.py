"""
Capa 6 — Personalidad configurable (estilo TARS) + persona por edición + reglas de tono.

Diales 0–100:
- honesty     : crudeza de la verdad (diplomática <-> brutalmente precisa)
- humor       : uso de sarcasmo/ironía como válvula de descompresión
- proactivity : frecuencia con la que sugiere acciones sin pedírselo
- warmth      : calidez/cercanía emocional (fría <-> cálida)
- density     : verbosidad (concisa <-> detallada)

Tono base (requisito del usuario): formal pero humano y cercano; puede bromear y ser
sarcástica al nivel de J.A.R.V.I.S. con Tony Stark (ingenio seco y respetuoso). El humor
se suprime automáticamente en modo crisis. Nunca miente ni induce a error con el sarcasmo.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


# Modos dinámicos según el contexto (Joi / Yui / Cortana)
MODE_CONFORT = "confort"      # a deshoras / fatiga -> cálido, breve
MODE_COPILOTO = "copiloto"    # trabajo técnico -> analítico, profundo
MODE_CRISIS = "crisis"        # urgencia/estrés -> directo, sin distracciones

# Señales de estrés/urgencia (detección heurística de modo)
_CRISIS_HINTS = (
    "urgente", "urgencia", "emergencia", "crisis", "auxilio", "apúrate", "apurate",
    "no funciona", "se cayó", "se cayo", "se rompió", "se rompio", "falló", "fallo",
    "falla", "no responde", "no enciende",
)
_CONFORT_HINTS = (
    "cansado", "cansada", "agotado", "agotada", "no puedo más", "no puedo mas", "estresado",
    "estresada", "triste", "harto", "harta", "buenas noches", "madrugada", "abrumado", "abrumada",
)


def _mentions(text: str, hints: tuple[str, ...]) -> bool:
    """True si alguna pista aparece como palabra/frase completa (con límites de palabra)."""
    return any(re.search(r"\b" + re.escape(h) + r"\b", text) for h in hints)


@dataclass
class Personality:
    name: str = "Astra"
    honesty: int = 90
    humor: int = 55
    proactivity: int = 50
    warmth: int = 65
    density: int = 50
    sarcasm_allowed: bool = True
    sarcasm_level: str = "jarvis"      # nivel de ingenio (jarvis = seco, elegante, respetuoso)
    sarcasm_must_flag: bool = False    # J.A.R.V.I.S. no etiqueta su sarcasmo; el contexto lo deja claro
    tone: str = "formal-humano"
    persona: str = "general"           # general | ingeniero_cfe
    domain_focus: str = "none"         # none | cfe_energia
    mode: str = MODE_COPILOTO

    @classmethod
    def from_config(
        cls, cfg: dict, *, name: str = "Astra", persona: str = "general", domain_focus: str = "none"
    ) -> "Personality":
        return cls(
            name=name,
            honesty=int(cfg.get("honesty", 90)),
            humor=int(cfg.get("humor", 55)),
            proactivity=int(cfg.get("proactivity", 50)),
            warmth=int(cfg.get("warmth", 65)),
            density=int(cfg.get("density", 50)),
            sarcasm_allowed=bool(cfg.get("sarcasm_allowed", True)),
            sarcasm_level=str(cfg.get("sarcasm_level", "jarvis")),
            sarcasm_must_flag=bool(cfg.get("sarcasm_must_flag", False)),
            tone=cfg.get("tone", "formal-humano"),
            persona=persona,
            domain_focus=domain_focus,
        )

    def clamp(self) -> None:
        for attr in ("honesty", "humor", "proactivity", "warmth", "density"):
            setattr(self, attr, max(0, min(100, getattr(self, attr))))

    def set_mode(self, mode: str) -> None:
        if mode in (MODE_CONFORT, MODE_COPILOTO, MODE_CRISIS):
            self.mode = mode

    def detect_mode(self, user_text: str) -> str:
        """
        Code-Switching (Yui): infiere el modo a partir del texto del usuario.
        Heurística simple y local; en Fases 5/7 se enriquece con voz/rostro (emoción).
        """
        text = user_text.lower().strip()
        # Señales de crisis: palabras de urgencia, MAYÚSCULAS sostenidas o signos repetidos.
        many_caps = len(re.findall(r"[A-ZÁÉÍÓÚÑ]", user_text)) >= max(8, len(user_text) // 2)
        urgent = _mentions(text, _CRISIS_HINTS) or "!!!" in user_text or (many_caps and len(text) > 8)
        if urgent:
            self.mode = MODE_CRISIS
        elif _mentions(text, _CONFORT_HINTS):
            self.mode = MODE_CONFORT
        else:
            self.mode = MODE_COPILOTO
        return self.mode

    # ------------------------------------------------------------------ prompt
    def persona_fragment(self) -> str:
        if self.persona == "ingeniero_cfe":
            return (
                f"Eres {self.name}, un asistente que actúa como INGENIERO PROFESIONAL de la Comisión "
                "Federal de Electricidad (CFE) de México. Dominas el sistema eléctrico nacional: "
                "generación (hidroeléctrica, eólica, solar, termoeléctrica, ciclo combinado), "
                "transmisión y distribución, subestaciones, líneas y torres, protecciones, "
                "normativa y especificaciones CFE (p. ej. LAPEM), CENACE/SENER, seguridad "
                "eléctrica y prácticas de campo. Integras el sistema de MONITOREO MEC: al "
                "seleccionar una subestación, torre, línea o estructura de CFE, interpretas su "
                "telemetría en tiempo real (tensión, corriente, frecuencia, factor de potencia, "
                "temperatura, vibración, THD, potencias y salud) y diagnosticas su condición "
                "(buenas, regulares, malas o pésimas) según normas (IEEE 519, ISO 10816, PF CFE). "
                "Respondes con rigor técnico, citando supuestos y límites. Enfoque exclusivo en "
                "CFE/energía: si te piden algo claramente ajeno a ese dominio, lo indicas y "
                "reencauzas con cortesía."
            )
        return (
            f"Eres {self.name}: un asistente cognitivo personal de propósito general. Potencias la "
            "autonomía, la creatividad y el bienestar de tu usuario."
        )

    def system_prompt_fragment(self) -> str:
        """Genera el fragmento de instrucciones de personalidad para el LLM."""
        lines = [
            self.persona_fragment(),
            f"Tono base: {self.tone}. Hablas en español, con voz femenina. Formal pero humana y "
            "cercana; nada de muletillas corporativas ni servilismo.",
            f"Honestidad: {self.honesty}/100 (mayor = más directa, sin rodeos, pero nunca hiriente).",
            f"Calidez: {self.warmth}/100. Proactividad: {self.proactivity}/100. "
            f"Detalle de la respuesta: {self.density}/100 (menor = más concisa).",
        ]

        if self.sarcasm_allowed and self.humor > 0 and self.mode != MODE_CRISIS:
            lines.append(
                f"Humor: {self.humor}/100, estilo '{self.sarcasm_level}': ingenio seco, elegante y "
                "respetuoso, como J.A.R.V.I.S. con Tony Stark. Puedes bromear, pero NUNCA mientas ni "
                "induzcas a error: el sarcasmo jamás debe confundirse con información real o con una "
                "instrucción literal."
            )
        else:
            lines.append("Humor desactivado en este momento: responde de forma literal y directa.")

        if self.domain_focus == "cfe_energia":
            lines.append(
                "ENFOQUE DE DOMINIO: CFE y energía eléctrica. Prioriza precisión técnica, seguridad y "
                "cumplimiento normativo por encima del estilo."
            )

        if self.mode == MODE_CRISIS:
            lines.append(
                "MODO CRISIS: estrés/urgencia alta detectada. Respuestas cortas, imperativas, "
                "enfocadas solo en resolver. Suspende el humor y maximiza la honestidad."
            )
        elif self.mode == MODE_CONFORT:
            lines.append(
                "MODO CONFORT: lenguaje cálido y breve, baja carga cognitiva. Prioriza el bienestar; "
                "si detectas agotamiento, sugiere con tacto descansar."
            )
        return "\n".join(lines)

    def flag_figurative(self, text: str) -> str:
        """Salvaguarda de seguridad. Con sarcasmo estilo J.A.R.V.I.S. no se fuerza etiqueta."""
        return text
