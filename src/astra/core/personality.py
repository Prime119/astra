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
        """Genera el prompt usando la base de las 16 IAs."""
        from .sixteen_ais import get_integrated_prompt
        return get_integrated_prompt()

    def flag_figurative(self, text: str) -> str:
        """Ya no señala sarcasmo — se expresa naturalmente."""
        return text
