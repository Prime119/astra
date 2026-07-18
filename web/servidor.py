"""
ASTRA — Servidor web con interfaz JARVIS.

Interfaz minimalista con disco/orbe animado estilo Iron Man 1.
Funciona sin internet (solo necesita Ollama corriendo local).
Voz natural via edge-tts (voces neuronales de Microsoft).

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
import threading
import hashlib
import psutil
from pathlib import Path
from datetime import datetime

from aiohttp import web

# Permitir importar astra
RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

from astra.core.orchestrator import Astra

# === EDGE-TTS (voz neuronal natural) ===
try:
    import edge_tts
    EDGE_TTS_DISPONIBLE = True
except ImportError:
    EDGE_TTS_DISPONIBLE = False
    print("   ⚠️ edge-tts no instalado. Instala con: pip install edge-tts")
    print("   La voz usará el sintetizador del navegador (menos natural).")

# Voz femenina neuronal — es-MX-DaliaNeural suena joven, natural y femenina
VOZ_EDGE = "es-MX-DaliaNeural"
# Alternativas si quieres cambiar:
# "es-MX-DaliaNeural"    — mexicana, joven, natural
# "es-ES-ElviraNeural"   — española, clara, profesional
# "es-AR-ElenaNeural"    — argentina, cálida
# "es-CO-SalomeNeural"   — colombiana, suave

# Carpeta para cache de audio generado
AUDIO_CACHE = RAIZ / "web" / "static" / "audio"
AUDIO_CACHE.mkdir(parents=True, exist_ok=True)

# Inicializar Astra (rápido, solo configura)
print("🌟 Iniciando Astra...")
astra = Astra.boot()
cerebro_online = astra.brain.is_local_available()
print(f"   Cerebro: {'✅ Online' if cerebro_online else '❌ Offline'}")
print(f"   Hardware: {astra.config.hardware.tier} ({astra.config.hardware.ram_gb}GB RAM)")
print(f"   Voz: {'✅ edge-tts (neuronal)' if EDGE_TTS_DISPONIBLE else '⚠️ navegador (básica)'}")

# Precalentar el modelo EN SEGUNDO PLANO (no bloquea el servidor)
modelo_listo = threading.Event()

def _precalentar():
    """Calienta el modelo en un hilo separado para que el servidor arranque al instante."""
    if not cerebro_online:
        modelo_listo.set()
        return
    print("   ⏳ Precalentando modelo en segundo plano...")
    try:
        astra.brain.think("hola")
        print("   ✅ Modelo precalentado — listo para responder rápido")
    except Exception:
        print("   ⚠️ No se pudo precalentar (la primera respuesta tardará más)")
    modelo_listo.set()

# Lanzar precalentamiento en hilo separado
threading.Thread(target=_precalentar, daemon=True).start()


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
    bloqueados = ["rm -rf", "format", "del /", "shutdown", "reboot", "mkfs"]
    if any(b in cmd.lower() for b in bloqueados):
        return "Comando bloqueado por seguridad. No ejecuto acciones destructivas."
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        salida = result.stdout[:1000] or result.stderr[:500] or "(sin salida)"
        return salida.strip()
    except subprocess.TimeoutExpired:
        return "Comando cancelado (tardó más de 10 segundos)."
    except Exception as e:
        return f"Error: {e}"


def limpiar_texto_para_voz(texto: str) -> str:
    """Limpia el texto para que suene natural al hablarlo."""
    import re
    limpio = texto
    limpio = re.sub(r'```[\s\S]*?```', '', limpio)     # bloques de código
    limpio = re.sub(r'\*\*', '', limpio)                # negrita
    limpio = re.sub(r'\*', '', limpio)                  # itálica
    limpio = re.sub(r'#+ ?', '', limpio)                # headers
    limpio = re.sub(r'- ', ', ', limpio)                # listas
    limpio = re.sub(r'[🚫⚠️🔥⚡💻🧠🕐📊\[\]{}|_~`<>]', '', limpio)
    limpio = re.sub(r'\(.*?\)', '', limpio)             # paréntesis
    limpio = re.sub(r'https?://\S+', '', limpio)       # URLs
    limpio = re.sub(r'\n+', ', ', limpio)              # newlines
    limpio = re.sub(r'\.{2,}', '.', limpio)            # ...
    limpio = re.sub(r',{2,}', ',', limpio)             # ,,
    limpio = re.sub(r':\s', ', ', limpio)              # :
    limpio = re.sub(r';\s', ', ', limpio)              # ;
    limpio = re.sub(r'\s+', ' ', limpio)               # espacios
    return limpio.strip()[:600]


async def generar_audio_edge(texto: str) -> str | None:
    """Genera audio con edge-tts y devuelve la ruta al archivo MP3."""
    if not EDGE_TTS_DISPONIBLE:
        return None
    
    limpio = limpiar_texto_para_voz(texto)
    if not limpio or len(limpio) < 3:
        return None
    
    # Usar hash del texto como nombre de archivo (cache)
    text_hash = hashlib.md5(limpio.encode()).hexdigest()[:12]
    audio_file = AUDIO_CACHE / f"{text_hash}.mp3"
    
    # Si ya existe en cache, reusar
    if audio_file.exists():
        return f"/static/audio/{audio_file.name}"
    
    try:
        communicate = edge_tts.Communicate(limpio, VOZ_EDGE, rate="+5%", pitch="+0Hz")
        await communicate.save(str(audio_file))
        return f"/static/audio/{audio_file.name}"
    except Exception as e:
        print(f"   ⚠️ Error edge-tts: {e}")
        return None


# === ENDPOINTS ===
async def handle_index(request):
    return web.FileResponse(RAIZ / "web" / "static" / "index.html")


async def handle_static(request):
    name = request.match_info["name"]
    path = RAIZ / "web" / "static" / name
    if path.exists():
        return web.FileResponse(path)
    return web.Response(status=404)


async def handle_audio_static(request):
    """Sirve archivos de audio generados."""
    name = request.match_info["name"]
    path = AUDIO_CACHE / name
    if path.exists():
        return web.FileResponse(path, headers={"Content-Type": "audio/mpeg"})
    return web.Response(status=404)


async def handle_chat(request):
    """Endpoint principal de chat con Astra."""
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"respuesta": "No entendí el mensaje. Intenta de nuevo."})
    texto = data.get("texto", "").strip()
    if not texto:
        return web.json_response({"respuesta": ""})

    # Si el modelo aún está precalentándose, esperar un poco
    if not modelo_listo.is_set():
        modelo_listo.wait(timeout=5.0)

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
        audio_url = await generar_audio_edge(respuesta)
        return web.json_response({"respuesta": respuesta, "sistema": info, "audio": audio_url})

    # Detectar si pide ejecutar algo
    if any(w in t for w in ["ejecuta", "corre", "abre", "run", "cmd"]):
        for trigger in ["ejecuta ", "corre ", "run "]:
            if trigger in t:
                cmd = texto[t.index(trigger) + len(trigger):]
                resultado = ejecutar_comando(cmd)
                respuesta = f"Ejecuté el comando. Resultado: {resultado}"
                audio_url = await generar_audio_edge(respuesta)
                return web.json_response({"respuesta": respuesta, "audio": audio_url})

    # Detectar hora/fecha
    if any(w in t for w in ["hora", "fecha", "día", "qué día"]):
        ahora = datetime.now()
        respuesta = f"Son las {ahora.strftime('%H:%M')} del {ahora.strftime('%d de %B de %Y')}."
        audio_url = await generar_audio_edge(respuesta)
        return web.json_response({"respuesta": respuesta, "audio": audio_url})

    # Incluir contexto de memoria/aprendizajes para que Astra recuerde
    memoria_ctx = astra.get_learning_context()
    
    # Chat normal con el LLM
    texto_con_instruccion = (
        "IMPORTANTE: Si el usuario escribe con errores ortográficos o palabras mal escritas, "
        "interpreta lo que quiso decir por contexto y responde normalmente. "
        "NO le corrijas la ortografía ni menciones el error. Solo responde al contenido.\n\n"
    )
    if memoria_ctx:
        texto_con_instruccion += f"[MEMORIA - Cosas que recuerdas del usuario]:\n{memoria_ctx}\n\n"
    texto_con_instruccion += f"Usuario dice: {texto}"
    
    loop = asyncio.get_event_loop()
    try:
        respuesta = await loop.run_in_executor(None, astra.handle, texto_con_instruccion)
    except Exception as e:
        respuesta = f"Disculpa, tuve un problema al procesar eso."

    # Aprendizaje autónomo: extraer hechos relevantes de la conversación
    asyncio.ensure_future(_aprender_de_conversacion(texto, respuesta))
    
    # Generar audio con voz neuronal
    audio_url = await generar_audio_edge(respuesta)
    return web.json_response({"respuesta": str(respuesta), "audio": audio_url})


async def _aprender_de_conversacion(user_text: str, response: str):
    """Extrae hechos/preferencias del usuario y los guarda en memoria persistente."""
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, astra.learn_from_interaction, user_text, response)
    except Exception:
        pass  # Aprendizaje es best-effort, nunca bloquea


async def handle_tts(request):
    """Genera audio bajo demanda para un texto dado."""
    try:
        data = await request.json()
    except Exception:
        return web.Response(status=400)
    texto = data.get("texto", "").strip()
    if not texto:
        return web.json_response({"audio": None})
    
    audio_url = await generar_audio_edge(texto)
    return web.json_response({"audio": audio_url})


async def handle_status(request):
    """Estado del sistema y de Astra."""
    return web.json_response({
        "astra": astra.status(),
        "sistema": obtener_info_sistema(),
        "edge_tts": EDGE_TTS_DISPONIBLE,
    })


async def handle_memory(request):
    """Devuelve los aprendizajes/memoria de Astra."""
    return web.json_response({
        "aprendizajes": astra.get_learnings(),
        "stats": astra.memory_stats(),
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
    app.router.add_get("/static/audio/{name}", handle_audio_static)
    app.router.add_post("/api/chat", handle_chat)
    app.router.add_post("/api/tts", handle_tts)
    app.router.add_get("/api/status", handle_status)
    app.router.add_get("/api/memory", handle_memory)

    print("=" * 50)
    print("  🌟 ASTRA — Interfaz Web JARVIS")
    print(f"  Voz: {'edge-tts neuronal (' + VOZ_EDGE + ')' if EDGE_TTS_DISPONIBLE else 'navegador (básica)'}")
    print("  Abriendo en http://localhost:3000")
    print("  Presiona Ctrl+C para detener")
    print("=" * 50)

    web.run_app(app, host="0.0.0.0", port=3000, print=None)


if __name__ == "__main__":
    main()
