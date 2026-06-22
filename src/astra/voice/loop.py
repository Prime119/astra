"""
Bucle de conversación por voz (Fase 1).

Flujo:  🎙️ escuchar -> 📝 transcribir -> 🧠 pensar -> 🔊 hablar -> repetir

En esta fase es escucha continua simple (sin wake word ni atención por cámara, que
llegan en fases posteriores). Di "adiós Astra" o "detente" para terminar.
"""
from __future__ import annotations

from ..core.orchestrator import Astra
from .stt import Ear, STTConfig
from .tts import TTSConfig, Voice


STOP_WORDS = ("adiós astra", "adios astra", "detente astra", "hasta luego astra")


def build_voice_io(astra: Astra) -> tuple[Ear, Voice]:
    cfg = astra.config
    stt = STTConfig(
        model_size=cfg.get("voice", "stt_model", default="small"),
        language=cfg.get("identity", "language", default="es"),
        device="cuda" if cfg.hardware.has_gpu else "cpu",
        compute_type="float16" if cfg.hardware.has_gpu else "int8",
    )
    tts = TTSConfig(
        voice_path=cfg.get("voice", "tts_voice_path", default=""),
        piper_binary=cfg.get("voice", "piper_binary", default="piper"),
        speak_aloud=bool(cfg.get("voice", "enabled", default=True)),
    )
    return Ear(stt), Voice(tts)


def run_voice_loop(astra: Astra) -> None:
    try:
        ear, voice = build_voice_io(astra)
    except Exception as exc:
        print(f"[Astra] No pude inicializar la voz: {exc}")
        return

    name = astra.config.name
    greeting = f"Hola, soy {name}. Te escucho."
    print(f"🔊 {greeting}")
    voice.speak(greeting)

    while True:
        try:
            print("🎙️  (escuchando...)")
            text = ear.listen()
        except Exception as exc:
            print(f"[Astra] Problema con el micrófono: {exc}")
            break

        if not text:
            continue
        print(f"📝 Tú: {text}")

        if any(sw in text.lower() for sw in STOP_WORDS):
            despedida = "Hasta luego. Aquí estaré cuando me necesites."
            print(f"🔊 {name}: {despedida}")
            voice.speak(despedida)
            break

        response = astra.handle(text)
        print(f"🔊 {name}: {response}\n")
        voice.speak(response)
