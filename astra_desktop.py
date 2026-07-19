"""
ASTRA — Lanzador Desktop (Electron + Python).

Inicia el backend Python SIN abrir el navegador, y luego abre la ventana Electron.

Uso:
    python astra_desktop.py
"""
import subprocess
import sys
import os
import time
import threading
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
os.environ["ASTRA_MODE"] = "desktop"  # Le dice al servidor que NO abra el navegador


def iniciar_electron():
    """Inicia Electron después de que el backend esté listo."""
    time.sleep(4)  # Esperar a que el backend arranque
    desktop_dir = RAIZ / "desktop"
    
    print("🖥️  Abriendo interfaz de escritorio...")
    subprocess.Popen(
        ["npx", "electron", "."],
        cwd=str(desktop_dir), shell=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )


if __name__ == "__main__":
    print("=" * 50)
    print("  🌟 ASTRA — Modo Desktop")
    print("  Backend: Python + Ollama (puerto 3000)")
    print("  Frontend: Electron + Babylon.js")
    print("  Ctrl+C para detener")
    print("=" * 50)
    
    # Lanzar Electron en un hilo (se abre después de 4 seg)
    electron_thread = threading.Thread(target=iniciar_electron, daemon=True)
    electron_thread.start()
    
    # Backend en el hilo principal (sin abrir navegador)
    sys.path.insert(0, str(RAIZ / "src"))
    sys.path.insert(0, str(RAIZ))
    from web.servidor import main
    main()
