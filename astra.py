"""
ASTRA — Lanzador simple.

Uso:
    python astra.py          → chat de texto
    python astra.py --voice  → conversación por voz
    python astra.py --status → solo muestra el estado del sistema
"""
import sys
from pathlib import Path

# Agregar la carpeta src al path para que encuentre el módulo
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from astra.main import main

if __name__ == "__main__":
    raise SystemExit(main())
