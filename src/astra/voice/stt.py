"""
Capa 5 — Oído (Speech-to-Text) con faster-whisper, 100% offline.

Captura audio del micrófono y lo transcribe a texto. Usa una detección simple de silencio
(VAD por energía) para saber cuándo terminaste de hablar, sin necesidad de presionar nada.

Dependencias (Fase 1): faster-whisper, sounddevice, numpy
Se importan de forma perezosa para que el núcleo arranque aunque no estén instaladas.
"""
from __future__ import annotations

from dataclasses import dataclass


SAMPLE_RATE = 16000  # Whisper trabaja a 16 kHz


@dataclass
class STTConfig:
    model_size: str = "small"      # tiny | base | small | medium
    language: str = "es"
    device: str = "auto"           # auto | cpu | cuda
    compute_type: str = "int8"     # int8 (CPU) | float16 (GPU)
    silence_threshold: float = 0.01
    silence_duration_s: float = 1.2
    max_record_s: float = 15.0


class Ear:
    def __init__(self, config: STTConfig | None = None) -> None:
        self.config = config or STTConfig()
        self._model = None

    def _load_model(self):
        if self._model is None:
            from faster_whisper import WhisperModel  # type: ignore

            device = self.config.device
            if device == "auto":
                device = "cpu"  # se sobreescribe a 'cuda' si hay GPU en config
            self._model = WhisperModel(
                self.config.model_size, device=device, compute_type=self.config.compute_type
            )
        return self._model

    def record_until_silence(self):
        """Graba del micrófono hasta detectar silencio. Devuelve audio float32 mono."""
        import numpy as np  # type: ignore
        import sounddevice as sd  # type: ignore

        block = int(SAMPLE_RATE * 0.1)  # bloques de 100 ms
        silence_blocks_needed = int(self.config.silence_duration_s / 0.1)
        max_blocks = int(self.config.max_record_s / 0.1)

        frames: list = []
        silent_run = 0
        spoke = False

        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32") as stream:
            for _ in range(max_blocks):
                data, _ = stream.read(block)
                mono = data[:, 0]
                frames.append(mono)
                rms = float(np.sqrt(np.mean(mono ** 2)))
                if rms >= self.config.silence_threshold:
                    spoke = True
                    silent_run = 0
                elif spoke:
                    silent_run += 1
                    if silent_run >= silence_blocks_needed:
                        break
        return np.concatenate(frames) if frames else np.zeros(0, dtype="float32")

    def transcribe(self, audio) -> str:
        """Transcribe un arreglo de audio float32 a texto."""
        model = self._load_model()
        segments, _ = model.transcribe(audio, language=self.config.language, vad_filter=True)
        return " ".join(seg.text.strip() for seg in segments).strip()

    def listen(self) -> str:
        """Graba hasta el silencio y transcribe en un solo paso."""
        audio = self.record_until_silence()
        if audio.size == 0:
            return ""
        return self.transcribe(audio)
