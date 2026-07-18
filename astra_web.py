"""
ASTRA — Interfaz Web JARVIS.

Abre una interfaz en el navegador con disco animado estilo Iron Man,
chat por texto/voz, y capacidades del sistema.

Uso:
    python astra_web.py

Se abre automáticamente en http://localhost:3000
Funciona sin internet (solo necesita Ollama corriendo local).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from web.servidor import main

if __name__ == "__main__":
    main()
