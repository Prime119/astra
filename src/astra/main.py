"""
Punto de entrada de Astra (Fase 0).

⚠️ Esta es una consola de DESARROLLO para verificar que los cimientos funcionan.
El producto final NO será una ventana de comandos: será una app ambiental con voz e
interfaz holográfica (Fases 1+). Esto es solo para probar el núcleo.

Uso:
    python -m astra.main          # muestra estado y un mini-chat de prueba
    python -m astra.main --status # solo el estado del sistema
"""
from __future__ import annotations

import json
import sys

from .core.orchestrator import Astra


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    astra = Astra.boot()

    print("=" * 60)
    print(f"  🌟 {astra.config.name} — núcleo iniciado (Fase 0)")
    print("=" * 60)
    print(json.dumps(astra.status(), indent=2, ensure_ascii=False))

    if "--status" in argv:
        return 0

    print("\n[Mini-chat de prueba — escribe 'salir' para terminar]\n")
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
