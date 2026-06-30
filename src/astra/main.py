"""
Punto de entrada de Astra.

⚠️ Esta es una consola de DESARROLLO para probar el núcleo y la voz. El producto final
NO será una ventana de comandos: será una app ambiental / servicio en segundo plano
(Fases 3/7).

Ediciones:
    --edition full   ASTRA Full (todas las capacidades; sin módulo Falcon)
    --edition cfe    ASTRA CFE  (enfocada en CFE; ingeniero profesional; con Falcon)
  (también se puede usar --full / --cfe, o la variable de entorno ASTRA_EDITION)

Uso:
    python -m astra                       # mini-chat de texto (edición full)
    python -m astra --cfe                  # mini-chat en la edición CFE
    python -m astra --status               # solo el estado del sistema
    python -m astra --check                 # diagnóstico de Ollama (¿está listo el cerebro?)
    python -m astra --seal                  # (dueño) sella el código: protección anti-modificación
    python -m astra --verify                # verifica la integridad del código (tamper-lock)
    python -m astra --say "hola astra"     # un solo turno (no interactivo)
    python -m astra --voice                # conversación por VOZ (Fase 1)
"""
from __future__ import annotations

import json
import sys

from .core.orchestrator import Astra


def _parse_edition(argv: list[str]) -> str | None:
    if "--cfe" in argv:
        return "cfe"
    if "--full" in argv:
        return "full"
    if "--edition" in argv:
        i = argv.index("--edition")
        if i + 1 < len(argv):
            return argv[i + 1]
    return None  # deja que load_config use ASTRA_EDITION o el valor por defecto


def _get_say(argv: list[str]) -> str | None:
    if "--say" in argv:
        i = argv.index("--say")
        if i + 1 < len(argv):
            return argv[i + 1]
    return None


def _print_brain_check(astra) -> None:
    """Diagnóstico amigable: hardware detectado + estado de Ollama + modelo elegido."""
    hw = astra.config.hardware
    d = astra.brain.diagnose()
    print("\n🖥️  Hardware detectado")
    print("-" * 44)
    print(f"RAM             : {hw.ram_gb} GB")
    print(f"GPU dedicada    : {'sí' if hw.has_gpu else 'no'}")
    print(f"CPUs            : {hw.cpu_count}")
    print(f"Nivel (tier)    : {hw.tier}  ->  modelo objetivo: {d['model']}")

    # Modelos INCLUIDOS (bundled) detectados en disco
    try:
        from pathlib import Path
        from .brain.provisioner import bundled_status
        bundled = astra.config.get("brain", "bundled_models", default={}) or {}
        if isinstance(bundled, dict) and bundled:
            mdir = Path(astra.config.paths.base_dir) / astra.config.get("brain", "bundled_models_dir", default="models")
            bs = bundled_status(hw.tier, bundled, mdir)
            print("\n📦 Modelos incluidos (en el programa)")
            print("-" * 44)
            print(f"Carpeta         : {bs['dir']}")
            for t, ok in bs["present"].items():
                print(f"  {t:<12}: {'✅ presente' if ok else '— no está'}")
            if bs["chosen_name"]:
                print(f"Se activará     : {bs['chosen_name']}  (sin internet)")
            else:
                print("Se activará     : (ninguno incluido; usaré modelos de Ollama si los hay)")
    except Exception:
        pass

    print("\n🧠 Diagnóstico del cerebro (Ollama)")
    print("-" * 44)
    print(f"Endpoint        : {d['endpoint']}")
    print(f"Ollama en línea : {'✅ sí' if d['reachable'] else '❌ no'}")
    if not d["reachable"]:
        print("\n⚠️  No detecto Ollama corriendo. Pasos:")
        print("   1) Instala Ollama:  https://ollama.com/download")
        print("   2) Ábrelo (queda en segundo plano en 127.0.0.1:11434).")
        print(f"   3) Descarga el modelo de tu equipo:  ollama pull {d['model']}")
        print("   4) Vuelve a ejecutar:  python -m astra --check")
        print("\n💡 Para tener los 3 y que cada equipo elija solo:")
        print("   ollama pull qwen2.5:3b-instruct")
        print("   ollama pull qwen2.5:7b-instruct")
        print("   ollama pull qwen2.5:14b-instruct")
        return
    print(f"Modelo elegido  : {d['model']}  (auto-seleccionado para este equipo)")
    print(f"Modelo de código: {d['coder_model']}")
    print(f"Modelos locales : {', '.join(d['available']) or '(ninguno)'}")
    if d["missing"]:
        print("\n⚠️  Faltan modelos. Descárgalos con:")
        for tag in d["missing"]:
            print(f"   ollama pull {tag}")
    else:
        print("\n✅ Todo listo. El cerebro de Astra/MEC está operativo.")


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    astra = Astra.boot(edition=_parse_edition(argv))

    print("=" * 60)
    print(f"  🌟 {astra.config.edition_name} — núcleo iniciado")
    print("=" * 60)
    print(json.dumps(astra.status(), indent=2, ensure_ascii=False))

    if "--status" in argv:
        return 0

    if "--check" in argv:
        _print_brain_check(astra)
        return 0

    if "--seal" in argv:
        if not astra.guardian.owner_present():
            print("\n⚠️  Sellar el sistema es una acción de DUEÑO. En el build protegido requerirá tu "
                  "rostro. Por ahora, ejecútalo con la sesión de dueño activa (ASTRA_OWNER=1).")
        digest = astra.guardian.seal()
        print(f"\n🔒 Sistema SELLADO por el dueño. Huella del código: {digest[:16]}…")
        print("Desde ahora, si alguien modifica el código sin tu autorización (tu rostro),")
        print("el sistema se bloqueará y no funcionará. Vuelve a sellar tras cambios legítimos.")
        return 0

    if "--verify" in argv:
        ok, reason = astra.guardian.verify()
        print(f"\n🛡️  Integridad del código: {'✅ OK' if ok else '❌ ALTERADO'} — {reason}")
        return 0

    if "--enroll-face" in argv:
        from .vision.face_id import FaceID
        fid = FaceID(astra.guardian.owner_path)
        print("\n" + fid.enroll(samples=8))
        return 0

    if "--verify-face" in argv:
        from .vision.face_id import FaceID
        fid = FaceID(astra.guardian.owner_path)
        res = fid.verify()
        if res is None:
            print("\n👁️  Face ID no disponible. " + fid.note())
        else:
            print(f"\n👁️  ¿Eres el creador?: {'✅ SÍ' if res else '❌ NO'}")
        return 0

    say = _get_say(argv)
    if say is not None:
        print(f"\nTú > {say}")
        print(f"{astra.config.name} > {astra.handle(say)}")
        return 0

    if "--voice" in argv:
        from .voice.loop import run_voice_loop

        run_voice_loop(astra)
        return 0

    # Modo texto interactivo (prueba del cerebro)
    print("\n[Mini-chat de texto — escribe 'salir' para terminar]\n")
    try:
        while True:
            user = input("Tú > ").strip()
            if user.lower() in {"salir", "exit", "quit"}:
                break
            if not user:
                continue
            print(f"{astra.config.name} > {astra.handle(user)}\n")
    except (EOFError, KeyboardInterrupt):
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
