"""
Capa 7 — Atención por cámara.

Objetivo: que NO haga falta repetir "Oye Astra" en cada frase. Cuando la cámara está
activa, Astra detecta tu rostro y hacia dónde miras:
  - Si miras a la pantalla y hablas  -> te está hablando a ELLA -> escucha y responde.
  - Si volteas a otro lado            -> entiende que no le hablas -> ignora.
  - Tras varios segundos sin atención -> entra en reposo (vuelve la wake word).

(Fase 0: contrato e interfaz. La detección real con MediaPipe Face/Gaze + VAD se
implementa en la Fase 7. Todo el procesamiento es LOCAL — Zero-Knowledge.)
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class AttentionState(Enum):
    LISTENING = "listening"   # mirando + hablando -> dirigido a Astra
    PASSIVE = "passive"       # presente pero no dirigido a Astra
    STANDBY = "standby"       # sin atención -> requiere wake word


@dataclass
class AttentionConfig:
    enabled: bool = True
    gaze_sensitivity: float = 0.6   # 0..1, mayor = más estricto para considerar "mirando"
    standby_seconds: int = 45


class AttentionMonitor:
    def __init__(self, config: AttentionConfig) -> None:
        self.config = config
        self.state = AttentionState.STANDBY

    def update(self, *, face_present: bool, looking_at_screen: bool, speaking: bool) -> AttentionState:
        if not self.config.enabled:
            self.state = AttentionState.STANDBY
            return self.state
        if face_present and looking_at_screen and speaking:
            self.state = AttentionState.LISTENING
        elif face_present:
            self.state = AttentionState.PASSIVE
        else:
            self.state = AttentionState.STANDBY
        return self.state
