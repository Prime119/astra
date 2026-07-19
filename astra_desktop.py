"""
ASTRA — Lanzador Desktop (Electron + Python).

Inicia el backend Python y luego abre la interfaz Electron.
La interfaz web sigue disponible como fallback en localhost:3000.

Uso:
    python astra_desktop.py

Requisitos:
    - Node.js instalado
    - npm install ejecutado en desktop/
    - Ollama corriendo
"""
import subprocess
import sys
import os
import time
import threading
from pathlib import Path

RAIZ = Path(__file__).resolve().parent

def iniciar_backend():
    """Inicia el servidor Python (cerebro de Astra)."""
    print("🌟 Iniciando cerebro de Astra...")
    sys.path.insert(0, str(RAIZ / "src"))
    sys.path.insert(0, str(RAIZ))
    from web.servidor import main as web_main
    web_main()

def iniciar_electron():
    """Inicia la interfaz Electron después de que el backend esté listo."""
    time.sleep(3)  # Esperar a que el backend arranque
    desktop_dir = RAIZ / "desktop"
    
    if not (desktop_dir / "node_modules").exists():
        print("📦 Instalando dependencias del frontend...")
        subprocess.run(["npm", "install"], cwd=str(desktop_dir), shell=True)
    
    print("🖥️ Abriendo interfaz de escritorio...")
    # Primero iniciar Vite dev server
    vite = subprocess.Popen(
        ["npx", "vite", "--port", "5173"],
        cwd=str(desktop_dir), shell=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    time.sleep(2)
    
    # Luego abrir Electron
    subprocess.Popen(
        ["npx", "electron", "."],
        cwd=str(desktop_dir), shell=True
    )

if __name__ == "__main__":
    print("=" * 50)
    print("  🌟 ASTRA — Modo Desktop")
    print("  Backend: Python + Ollama")
    print("  Frontend: Electron + Vue + Babylon.js")
    print("=" * 50)
    
    # Lanzar Electron en un hilo
    electron_thread = threading.Thread(target=iniciar_electron, daemon=True)
    electron_thread.start()
    
    # Backend en el hilo principal
    iniciar_backend()
