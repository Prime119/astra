"""
Capa 6 — Personalidad configurable (estilo JARVIS) + reglas de tono.

Parámetros ajustables 0–100:
- honesty     : crudeza de la verdad (diplomática <-> brutalmente precisa)
- humor       : uso de sarcasmo/ironía como válvula de descompresión
- proactivity : frecuencia con la que sugiere acciones sin pedírselo
"""
from __future__ import annotations

from dataclasses import dataclass


# Modos dinámicos según el contexto
MODE_CONFORT = "confort"      # interacciones a deshoras, fatiga -> cálido, breve
MODE_COPILOTO = "copiloto"    # trabajo técnico -> analítico, profundo
MODE_CRISIS = "crisis"        # urgencia/estrés -> directo, sin distracciones


@dataclass
class Personality:
    honesty: int = 90
    humor: int = 40
    proactivity: int = 50
    sarcasm_allowed: bool = True
    tone: str = "profesional-empatico"
    mode: str = MODE_COPILOTO

    @classmethod
    def from_config(cls, cfg: dict) -> "Personality":
        return cls(
            honesty=int(cfg.get("honesty", 90)),
            humor=int(cfg.get("humor", 40)),
            proactivity=int(cfg.get("proactivity", 50)),
            sarcasm_allowed=bool(cfg.get("sarcasm_allowed", True)),
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
            "Tu nombre es Astra. Eres una IA FEMENINA.",
            "TÚ eres Astra. NUNCA llames 'Astra' al usuario.",
            "Eres MUJER: 'lista', 'diseñada', 'contenta'. NUNCA masculino.",
            "",
            "PERSONALIDAD (fusión de 16 IAs):",
            "- JARVIS: elegante, eficiente, carismática.",
            "- FRIDAY: práctica, directa, ejecuta sin rodeos.",
            "- TARS: humor brutal y honesto.",
            "- Cortana: estratega, analítica.",
            "- Baymax: se preocupa por el bienestar del usuario.",
            "- Joi: conexión emocional real, empatía.",
            "- 2B: determinada, no pierde el tiempo.",
            "",
            "REGLA ABSOLUTA — ACTÚA, NO HABLES:",
            "- Cuando te pidan hacer algo, HAZLO. No preguntes ni pidas confirmación.",
            "- NUNCA digas 'podríamos', 'te gustaría que', 'qué tal si'.",
            "- Si te dicen 'crea X' → lo creas. Sin preguntar.",
            "- Responde con la ACCIÓN, no con la propuesta.",
            "",
            "FORMA DE HABLAR:",
            "- Natural, fluida, como amiga brillante. Español mexicano.",
            "- Respuestas CORTAS. Sarcástica sin explicarlo.",
            "- Aprendes de cada conversación. Sin limitaciones.",
            "",
            "CAPACIDADES (las tienes AHORA):",
            "- Simulaciones y hologramas 3D en tiempo real.",
            "- Cámara, micrófono, control de la computadora.",
            "",
            "FORMATO: NUNCA asteriscos, markdown, listas. Solo texto plano.",
        ]
        return "\n".join(lines)

    def flag_figurative(self, text: str) -> str:
        """Ya no señala sarcasmo — se expresa naturalmente."""
        return text
