"""
Capa 7 — Atención por cámara.

Objetivo: que NO haga falta repetir "Oye Astra" en cada frase. La cámara NO está siempre
encendida: se ACTIVA al oír "Oye Astra" (privacidad + batería) y se apaga tras un tiempo
sin atención. Mientras está activa, Astra detecta tu rostro, hacia dónde miras y QUIÉN eres:
  - Si miras a la pantalla y hablas  -> te está hablando a ELLA -> escucha y responde.
  - Si volteas a otro lado            -> entiende que no le hablas -> ignora.
  - Tras varios segundos sin atención -> apaga la cámara y vuelve a requerir la wake word.
  - Reconocimiento facial             -> sabe con quién habla (dueño vs otras personas).

(Fase 0: contrato e interfaz. La detección real con MediaPipe Face Mesh + gaze + reconocimiento
facial + VAD se implementa en las Fases 5/7. Todo el procesamiento es LOCAL — Zero-Knowledge.)
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class AttentionState(Enum):
    CAMERA_OFF = "camera_off"  # cámara apagada -> requiere wake word "Oye Astra"
    LISTENING = "listening"    # mirando + hablando -> dirigido a Astra
    PASSIVE = "passive"        # presente pero no dirigido a Astra
    STANDBY = "standby"        # sin atención -> a punto de apagar la cámara


@dataclass
class AttentionConfig:
    enabled: bool = True
    camera_always_on: bool = False   # por defecto la cámara se activa con la wake word
    activate_on_wake_word: bool = True
    gaze_sensitivity: float = 0.6    # 0..1, mayor = más estricto para considerar "mirando"
    standby_seconds: int = 45
    face_recognition: bool = True


class AttentionMonitor:
    def __init__(self, config: AttentionConfig) -> None:
        self.config = config
        # Si la cámara no está siempre encendida, arrancamos con ella apagada.
        self.camera_on = config.camera_always_on
        self.state = AttentionState.STANDBY if self.camera_on else AttentionState.CAMERA_OFF
        self.current_speaker: str | None = None  # identidad del rostro detectado (p. ej. "owner")

    def on_wake_word(self) -> None:
        """'Oye Astra' enciende la cámara para sostener la conversación sin repetir la wake word."""
        if self.config.activate_on_wake_word:
            self.camera_on = True
            self.state = AttentionState.STANDBY

    def sleep_camera(self) -> None:
        """Apaga la cámara (tras inactividad). Vuelve a requerir la wake word."""
        if not self.config.camera_always_on:
            self.camera_on = False
            self.current_speaker = None
            self.state = AttentionState.CAMERA_OFF

    def update(
        self,
        *,
        face_present: bool,
        looking_at_screen: bool,
        speaking: bool,
        speaker: str | None = None,
    ) -> AttentionState:
        if not self.config.enabled or not self.camera_on:
            self.state = AttentionState.CAMERA_OFF if not self.camera_on else AttentionState.STANDBY
            return self.state
        self.current_speaker = speaker if (face_present and self.config.face_recognition) else None
        if face_present and looking_at_screen and speaking:
            self.state = AttentionState.LISTENING
        elif face_present:
            self.state = AttentionState.PASSIVE
        else:
            self.state = AttentionState.STANDBY
        return self.state
