"""
Punto de entrada de Astra.

⚠️ Esta es una consola de DESARROLLO para probar el núcleo y la voz. El producto final
NO será una ventana de comandos: será una app con interfaz propia (por definir en fases futuras).

Uso:
    python -m astra.main            # mini-chat de texto (prueba del cerebro)
    python -m astra.main --status   # solo el estado del sistema
    python -m astra.main --voice    # conversación por VOZ (Fase 1)
"""
from __future__ import annotations

import json
import sys

from .core.orchestrator import Astra


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    astra = Astra.boot()

    print("=" * 60)
    print(f"  🌟 {astra.config.name} — núcleo iniciado")
    print("=" * 60)
    print(json.dumps(astra.status(), indent=2, ensure_ascii=False))

    if "--status" in argv:
        return 0

    if "--voice" in argv:
        from .voice.loop import run_voice_loop

        run_voice_loop(astra)
        return 0

    # Modo texto (prueba del cerebro)
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
