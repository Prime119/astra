"""
Capa 5 — Voz (Text-to-Speech) con Piper, voz femenina en español, 100% offline.

Estrategia de reproducción (en orden, lo que esté disponible):
1. Paquete Python `piper` (genera audio en memoria) + sounddevice para reproducir.
2. Binario `piper` externo por subprocess (modo portátil clásico) -> archivo WAV -> reproducir.
3. Fallback: imprime el texto (para que el núcleo nunca se rompa por falta de audio).

Las voces de Piper son archivos .onnx (+ .onnx.json). Se descargan aparte y se apuntan
en la config (voice/tts_voice_path).
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
import wave
from dataclasses import dataclass
from pathlib import Path


@dataclass
class TTSConfig:
    voice_path: str = ""           # ruta al modelo .onnx de la voz (ej. es_MX-...-medium.onnx)
    piper_binary: str = "piper"    # nombre/ruta del ejecutable piper (modo portátil)
    speak_aloud: bool = True


class Voice:
    def __init__(self, config: TTSConfig | None = None) -> None:
        self.config = config or TTSConfig()
        self._py_voice = None

    # ----------------------------------------------------------- carga perezosa
    def _try_python_piper(self):
        if self._py_voice is not None:
            return self._py_voice
        try:
            from piper import PiperVoice  # type: ignore

            if self.config.voice_path and Path(self.config.voice_path).exists():
                self._py_voice = PiperVoice.load(self.config.voice_path)
                return self._py_voice
        except Exception:
            pass
        return None

    # ----------------------------------------------------------------- hablar
    def speak(self, text: str) -> None:
        if not text:
            return
        if not self.config.speak_aloud:
            print(f"🔊 Astra (texto): {text}")
            return

        # 1) Piper como paquete Python
        voice = self._try_python_piper()
        if voice is not None and self._speak_with_python(voice, text):
            return

        # 2) Piper como binario externo
        if self._speak_with_binary(text):
            return

        # 3) Fallback
        print(f"🔊 Astra (voz no disponible, muestro texto): {text}")

    def _speak_with_python(self, voice, text: str) -> bool:
        try:
            import io

            import numpy as np  # type: ignore
            import sounddevice as sd  # type: ignore

            buf = io.BytesIO()
            with wave.open(buf, "wb") as wf:
                voice.synthesize(text, wf)
            buf.seek(0)
            with wave.open(buf, "rb") as wf:
                rate = wf.getframerate()
                frames = wf.readframes(wf.getnframes())
            audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
            sd.play(audio, rate)
            sd.wait()
            return True
        except Exception:
            return False

    def _speak_with_binary(self, text: str) -> bool:
        binary = shutil.which(self.config.piper_binary) or self.config.piper_binary
        if not self.config.voice_path:
            return False
        try:
            tmp = Path(tempfile.gettempdir()) / "astra_tts.wav"
            proc = subprocess.run(
                [binary, "--model", self.config.voice_path, "--output_file", str(tmp)],
                input=text.encode("utf-8"),
                capture_output=True,
                timeout=60,
            )
            if proc.returncode != 0 or not tmp.exists():
                return False
            self._play_wav(tmp)
            return True
        except Exception:
            return False

    def _play_wav(self, path: Path) -> None:
        import numpy as np  # type: ignore
        import sounddevice as sd  # type: ignore

        with wave.open(str(path), "rb") as wf:
            rate = wf.getframerate()
            frames = wf.readframes(wf.getnframes())
        audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
        sd.play(audio, rate)
        sd.wait()
