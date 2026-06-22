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


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    astra = Astra.boot(edition=_parse_edition(argv))

    print("=" * 60)
    print(f"  🌟 {astra.config.edition_name} — núcleo iniciado")
    print("=" * 60)
    print(json.dumps(astra.status(), indent=2, ensure_ascii=False))

    if "--status" in argv:
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
