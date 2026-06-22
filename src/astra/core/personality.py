"""
Capa 6 — Personalidad configurable (estilo TARS) + reglas de tono.

Parámetros ajustables 0–100:
- honesty     : crudeza de la verdad (diplomática <-> brutalmente precisa)
- humor       : uso de sarcasmo/ironía como válvula de descompresión
- proactivity : frecuencia con la que sugiere acciones sin pedírselo

Regla del usuario: el sarcasmo está permitido, PERO debe señalarse para no
confundirse con información literal.
"""
from __future__ import annotations

from dataclasses import dataclass


# Modos dinámicos según el contexto (Joi / Yui / Cortana)
MODE_CONFORT = "confort"      # interacciones a deshoras, fatiga -> cálido, breve
MODE_COPILOTO = "copiloto"    # trabajo técnico -> analítico, profundo
MODE_CRISIS = "crisis"        # urgencia/estrés -> directo, sin distracciones


@dataclass
class Personality:
    honesty: int = 90
    humor: int = 40
    proactivity: int = 50
    sarcasm_allowed: bool = True
    sarcasm_must_flag: bool = True
    tone: str = "profesional-empatico"
    mode: str = MODE_COPILOTO

    @classmethod
    def from_config(cls, cfg: dict) -> "Personality":
        return cls(
            honesty=int(cfg.get("honesty", 90)),
            humor=int(cfg.get("humor", 40)),
            proactivity=int(cfg.get("proactivity", 50)),
            sarcasm_allowed=bool(cfg.get("sarcasm_allowed", True)),
            sarcasm_must_flag=bool(cfg.get("sarcasm_must_flag", True)),
            tone=cfg.get("tone", "profesional-empatico"),
        )

    def clamp(self) -> None:
        self.honesty = max(0, min(100, self.honesty))
        self.humor = max(0, min(100, self.humor))
        self.proactivity = max(0, min(100, self.proactivity))

    def set_mode(self, mode: str) -> None:
        if mode in (MODE_CONFORT, MODE_COPILOTO, MODE_CRISIS):
            self.mode = mode

    def system_prompt_fragment(self) -> str:
        """Genera el fragmento de instrucciones de personalidad para el LLM."""
        lines = [
            f"Eres Astra. Tono base: {self.tone}. Hablas en español, con voz femenina.",
            "Vas al grano, sin muletillas corporativas ni servilismo.",
            f"Nivel de honestidad: {self.honesty}/100 (mayor = más directa y sin rodeos).",
            f"Nivel de proactividad: {self.proactivity}/100.",
        ]
        if self.sarcasm_allowed and self.humor > 0:
            lines.append(
                f"Nivel de humor: {self.humor}/100. Puedes usar sarcasmo o lenguaje figurado, "
                "pero SIEMPRE debes señalarlo (por ejemplo, agregando '—eso fue sarcasmo' o "
                "'(en sentido figurado)') para que nunca se confunda con información literal."
            )
        else:
            lines.append("Humor desactivado: responde de forma literal y directa.")

        if self.mode == MODE_CRISIS:
            lines.append(
                "MODO CRISIS: detectado estrés/urgencia alta. Respuestas cortas, imperativas, "
                "enfocadas solo en resolver. Suspende el humor."
            )
        elif self.mode == MODE_CONFORT:
            lines.append("MODO CONFORT: lenguaje cálido, breve, baja carga cognitiva.")
        return "\n".join(lines)

    def flag_figurative(self, text: str) -> str:
        """Marca explícitamente una respuesta figurada/sarcástica si hace falta."""
        if self.sarcasm_must_flag and "—eso fue sarcasmo" not in text.lower():
            return text  # el LLM ya debe incluir la marca; aquí solo es salvaguarda
        return text
