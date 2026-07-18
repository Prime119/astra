"""
ASTRA — Servidor web con interfaz JARVIS.

Interfaz minimalista con disco/orbe animado estilo Iron Man 1.
Funciona sin internet (solo necesita Ollama corriendo local).

Ejecutar: python astra_web.py
Se abre en http://localhost:3000
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import platform
import subprocess
import webbrowser
import psutil
from pathlib import Path
from datetime import datetime

from aiohttp import web

# Permitir importar astra
RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

from astra.core.orchestrator import Astra

# Inicializar Astra
print("🌟 Iniciando Astra...")
astra = Astra.boot()
print(f"   Cerebro: {'✅ Online' if astra.brain.is_local_available() else '❌ Offline'}")
print(f"   Hardware: {astra.config.hardware.tier} ({astra.config.hardware.ram_gb}GB RAM)")


# === CAPACIDADES DEL SISTEMA ===
def obtener_info_sistema() -> dict:
    """Info del sistema operativo, CPU, RAM, disco."""
    return {
        "os": f"{platform.system()} {platform.release()}",
        "cpu": platform.processor() or "Desconocido",
        "cpu_uso": psutil.cpu_percent(interval=0.5),
        "ram_total_gb": round(psutil.virtual_memory().total / (1024**3), 1),
        "ram_usada_gb": round(psutil.virtual_memory().used / (1024**3), 1),
        "ram_pct": psutil.virtual_memory().percent,
        "disco_total_gb": round(psutil.disk_usage('/').total / (1024**3), 1) if os.name != 'nt' else round(psutil.disk_usage('C:\\').total / (1024**3), 1),
        "disco_pct": psutil.disk_usage('/').percent if os.name != 'nt' else psutil.disk_usage('C:\\').percent,
        "hora": datetime.now().strftime("%H:%M:%S"),
        "fecha": datetime.now().strftime("%d de %B de %Y"),
        "uptime_h": round((datetime.now() - datetime.fromtimestamp(psutil.boot_time())).total_seconds() / 3600, 1),
    }


def ejecutar_comando(cmd: str) -> str:
    """Ejecuta un comando del sistema (con límites de seguridad)."""
    # Comandos bloqueados por seguridad
    bloqueados = ["rm -rf", "format", "del /", "shutdown", "reboot", "mkfs"]
    if any(b in cmd.lower() for b in bloqueados):
        return "🚫 Comando bloqueado por seguridad. No ejecuto acciones destructivas."
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        salida = result.stdout[:1000] or result.stderr[:500] or "(sin salida)"
        return salida.strip()
    except subprocess.TimeoutExpired:
        return "⏱️ Comando cancelado (tardó más de 10 segundos)."
    except Exception as e:
        return f"Error: {e}"


# === ENDPOINTS ===
async def handle_index(request):
    return web.FileResponse(RAIZ / "web" / "static" / "index.html")


async def handle_static(request):
    name = request.match_info["name"]
    path = RAIZ / "web" / "static" / name
    if path.exists():
        return web.FileResponse(path)
    return web.Response(status=404)


async def handle_chat(request):
    """Endpoint principal de chat con Astra."""
    data = await request.json()
    texto = data.get("texto", "").strip()
    if not texto:
        return web.json_response({"respuesta": ""})

    # Detectar si pide info del sistema
    t = texto.lower()
    if any(w in t for w in ["sistema", "ram", "cpu", "disco", "hardware", "computadora", "pc"]):
        info = obtener_info_sistema()
        contexto = (f"[INFO DEL SISTEMA: {info['os']}, CPU al {info['cpu_uso']}%, "
                    f"RAM {info['ram_usada_gb']}/{info['ram_total_gb']}GB ({info['ram_pct']}%), "
                    f"Disco {info['disco_pct']}%, Uptime {info['uptime_h']}h]")
        texto_con_ctx = f"{contexto}\n\nEl usuario pregunta: {texto}"
        loop = asyncio.get_event_loop()
        respuesta = await loop.run_in_executor(None, astra.handle, texto_con_ctx)
        return web.json_response({"respuesta": respuesta, "sistema": info})

    # Detectar si pide ejecutar algo
    if any(w in t for w in ["ejecuta", "corre", "abre", "run", "cmd"]):
        # Extraer el comando (después de "ejecuta", "corre", etc.)
        for trigger in ["ejecuta ", "corre ", "run "]:
            if trigger in t:
                cmd = texto[t.index(trigger) + len(trigger):]
                resultado = ejecutar_comando(cmd)
                return web.json_response({"respuesta": f"Ejecuté el comando. Resultado:\n```\n{resultado}\n```"})

    # Detectar hora/fecha
    if any(w in t for w in ["hora", "fecha", "día", "qué día"]):
        ahora = datetime.now()
        respuesta = f"Son las {ahora.strftime('%H:%M')} del {ahora.strftime('%d de %B de %Y')}."
        return web.json_response({"respuesta": respuesta})

    # Chat normal con el LLM
    loop = asyncio.get_event_loop()
    respuesta = await loop.run_in_executor(None, astra.handle, texto)
    return web.json_response({"respuesta": respuesta})


async def handle_status(request):
    """Estado del sistema y de Astra."""
    return web.json_response({
        "astra": astra.status(),
        "sistema": obtener_info_sistema(),
    })


# === APP ===
async def on_startup(app):
    loop = asyncio.get_event_loop()
    loop.call_later(1.5, lambda: webbrowser.open("http://localhost:3000"))


def main():
    app = web.Application()
    app.on_startup.append(on_startup)
    app.router.add_get("/", handle_index)
    app.router.add_get("/static/{name}", handle_static)
    app.router.add_post("/api/chat", handle_chat)
    app.router.add_get("/api/status", handle_status)

    print("=" * 50)
    print("  🌟 ASTRA — Interfaz Web JARVIS")
    print("  Abriendo en http://localhost:3000")
    print("  Presiona Ctrl+C para detener")
    print("=" * 50)

    web.run_app(app, host="0.0.0.0", port=3000, print=None)


if __name__ == "__main__":
    main()
