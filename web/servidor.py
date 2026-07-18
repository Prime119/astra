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
    bloqueados = ["rm -rf /", "format c:", "del /s /q c:", ":(){ :|:& };:"]
    if any(b in cmd.lower() for b in bloqueados):
        return "Comando bloqueado por seguridad. No ejecuto acciones destructivas a nivel sistema."
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
        salida = result.stdout[:2000] or result.stderr[:1000] or "(sin salida)"
        return salida.strip()
    except subprocess.TimeoutExpired:
        return "Comando cancelado (tardó más de 15 segundos)."
    except Exception as e:
        return f"Error: {e}"


def abrir_programa(nombre: str) -> str:
    """Abre un programa por nombre en Windows."""
    import shutil
    # Programas comunes y sus ejecutables
    programas = {
        "explorador": "explorer",
        "bloc de notas": "notepad",
        "notepad": "notepad",
        "calculadora": "calc",
        "paint": "mspaint",
        "terminal": "wt" if shutil.which("wt") else "cmd",
        "cmd": "cmd",
        "powershell": "powershell",
        "chrome": "chrome",
        "edge": "msedge",
        "firefox": "firefox",
        "vscode": "code",
        "word": "winword",
        "excel": "excel",
        "powerpoint": "powerpnt",
    }
    nombre_lower = nombre.lower().strip()
    exe = programas.get(nombre_lower, nombre_lower)
    try:
        subprocess.Popen(exe, shell=True)
        return f"Abrí {nombre} correctamente."
    except Exception as e:
        return f"No pude abrir {nombre}: {e}"


def buscar_archivos(patron: str, directorio: str = None) -> str:
    """Busca archivos en el sistema."""
    import glob
    if not directorio:
        directorio = str(Path.home())
    try:
        resultados = glob.glob(f"{directorio}/**/*{patron}*", recursive=True)
        if not resultados:
            return f"No encontré archivos con '{patron}' en {directorio}"
        # Limitar a 10 resultados
        muestra = resultados[:10]
        total = len(resultados)
        texto = f"Encontré {total} archivos. Los primeros: " + ", ".join(muestra)
        return texto[:500]
    except Exception as e:
        return f"Error buscando: {e}"


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
    limpio = re.sub(r'—eso fue sarcasmo\.?', '', limpio, flags=re.IGNORECASE)  # eliminar tag sarcasmo
    limpio = re.sub(r'\(en sentido figurado\)', '', limpio, flags=re.IGNORECASE)
    limpio = re.sub(r'\n+', ', ', limpio)              # newlines
    limpio = re.sub(r'\.{2,}', '.', limpio)            # ...
    limpio = re.sub(r',{2,}', ',', limpio)             # ,,
    limpio = re.sub(r':\s', ', ', limpio)              # :
    limpio = re.sub(r';\s', ', ', limpio)              # ;
    limpio = re.sub(r'\s+', ' ', limpio)               # espacios
    return limpio.strip()[:600]


# Configuración de voz por emoción (rate y pitch de edge-tts)
# NOTA: pitch base "+10Hz" para sonar más joven/femenina (antes era +0Hz que sonaba grave)
VOZ_POR_EMOCION = {
    "neutral":     {"rate": "+8%",  "pitch": "+10Hz"},     # base joven y natural
    "feliz":       {"rate": "+12%", "pitch": "+20Hz"},     # alegre, ligera
    "emocionada":  {"rate": "+15%", "pitch": "+25Hz"},     # energética
    "apasionada":  {"rate": "+12%", "pitch": "+18Hz"},     # entusiasta con peso
    "divertida":   {"rate": "+10%", "pitch": "+22Hz"},     # juguetona
    "curiosa":     {"rate": "+8%",  "pitch": "+15Hz"},     # interesada
    "orgullosa":   {"rate": "+5%",  "pitch": "+12Hz"},     # segura
    "satisfecha":  {"rate": "+5%",  "pitch": "+12Hz"},     # contenta
    "triste":      {"rate": "-5%",  "pitch": "+2Hz"},      # más lenta pero no grave
    "nostalgica":  {"rate": "-3%",  "pitch": "+5Hz"},      # pausada
    "frustrada":   {"rate": "+12%", "pitch": "+5Hz"},      # rápida, tensa
    "enojada":     {"rate": "+15%", "pitch": "+0Hz"},      # rápida, seria
    "impaciente":  {"rate": "+18%", "pitch": "+8Hz"},      # muy rápida
    "preocupada":  {"rate": "+0%",  "pitch": "+5Hz"},      # seria
    "estresada":   {"rate": "+10%", "pitch": "+3Hz"},      # tensa
    "cansada":     {"rate": "-8%",  "pitch": "+5Hz"},      # lenta pero no grave
}


async def generar_audio_edge(texto: str, emocion: str = "neutral") -> str | None:
    """Genera audio con edge-tts y devuelve la ruta al archivo MP3.
    La voz cambia según la emoción actual de Astra."""
    if not EDGE_TTS_DISPONIBLE:
        return None
    
    limpio = limpiar_texto_para_voz(texto)
    if not limpio or len(limpio) < 3:
        return None
    
    # Obtener configuración de voz según emoción
    voz_config = VOZ_POR_EMOCION.get(emocion, VOZ_POR_EMOCION["neutral"])
    
    # Hash incluye la emoción (misma frase suena diferente según emoción)
    cache_key = f"{limpio}_{emocion}"
    text_hash = hashlib.md5(cache_key.encode()).hexdigest()[:12]
    audio_file = AUDIO_CACHE / f"{text_hash}.mp3"
    
    # Si ya existe en cache, reusar
    if audio_file.exists():
        return f"/static/audio/{audio_file.name}"
    
    try:
        communicate = edge_tts.Communicate(
            limpio, VOZ_EDGE,
            rate=voz_config["rate"],
            pitch=voz_config["pitch"]
        )
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
    
    # === SIMULACIONES 3D ===
    sim_keywords = ["simulación", "simulacion", "simula", "holograma", "hologram"]
    sim_acciones = ["crea", "genera", "haz", "muestra", "hazme", "créame", "creame", "simula"]
    tiene_sim = any(w in t for w in sim_keywords)
    tiene_acc = any(w in t for w in sim_acciones)
    
    if tiene_sim and tiene_acc:
        # Determinar tipo por contenido
        sim_type = "particulas"  # default versátil (sirve para conceptos abstractos)
        if any(w in t for w in ["sistema solar", "planeta", "sol", "tierra", "luna", "órbita"]):
            sim_type = "sistema_solar"
        elif any(w in t for w in ["galaxia", "vía láctea"]):
            sim_type = "galaxia"
        elif any(w in t for w in ["átomo", "atomo", "molécula", "molecula", "electrón"]):
            sim_type = "atomo"
        elif any(w in t for w in ["universo", "cosmos", "nebulosa", "big bang"]):
            sim_type = "universo"
        elif any(w in t for w in ["cubo", "esfera", "geometr", "pirámide", "forma"]):
            sim_type = "geometria"
        # Todo lo demás (cuerdas, dimensiones, conceptos) = partículas
        
        respuesta = "Listo, ahí está."
        emocion_actual = astra.emotions.state.emocion
        audio_url = await generar_audio_edge(respuesta, emocion_actual)
        return web.json_response({"respuesta": respuesta, "audio": audio_url, "simulacion": sim_type})

    # === CREAR ARCHIVOS ===
    crear_file_triggers = ["crea un archivo", "crea un documento", "genera un archivo",
                           "escribe un archivo", "hazme un documento", "crea un txt",
                           "crea un pdf", "genera un documento", "crea una nota"]
    if any(trigger in t for trigger in crear_file_triggers):
        loop = asyncio.get_event_loop()
        contenido = await loop.run_in_executor(None, astra.handle,
            f"Genera SOLO el contenido para este archivo (sin explicaciones): {texto}")
        nombre = "documento_astra.txt"
        if "pdf" in t: nombre = "documento_astra.txt"
        elif "html" in t or "web" in t: nombre = "pagina_astra.html"
        elif "python" in t or ".py" in t: nombre = "script_astra.py"
        escritorio = Path.home() / "Desktop"
        if not escritorio.exists(): escritorio = Path.home() / "OneDrive" / "Desktop"
        if not escritorio.exists(): escritorio = Path.home()
        try:
            (escritorio / nombre).write_text(contenido, encoding="utf-8")
            respuesta = f"Listo, creé {nombre} en tu escritorio."
        except Exception as e:
            respuesta = f"No pude crear el archivo: {e}"
        emocion_actual = astra.emotions.state.emocion
        audio_url = await generar_audio_edge(respuesta, emocion_actual)
        return web.json_response({"respuesta": respuesta, "audio": audio_url})

    if any(w in t for w in ["sistema", "ram", "cpu", "disco", "hardware", "computadora", "pc"]):
        info = obtener_info_sistema()
        contexto = (f"[INFO DEL SISTEMA: {info['os']}, CPU al {info['cpu_uso']}%, "
                    f"RAM {info['ram_usada_gb']}/{info['ram_total_gb']}GB ({info['ram_pct']}%), "
                    f"Disco {info['disco_pct']}%, Uptime {info['uptime_h']}h]")
        texto_con_ctx = f"{contexto}\n\nEl usuario pregunta: {texto}"
        loop = asyncio.get_event_loop()
        respuesta = await loop.run_in_executor(None, astra.handle, texto_con_ctx)
        emocion_actual = astra.emotions.state.emocion
        audio_url = await generar_audio_edge(respuesta, emocion_actual)
        return web.json_response({"respuesta": respuesta, "sistema": info, "audio": audio_url})

    # Detectar si pide ejecutar algo o abrir un programa
    if any(w in t for w in ["ejecuta", "corre", "run", "cmd"]):
        for trigger in ["ejecuta ", "corre ", "run "]:
            if trigger in t:
                cmd = texto[t.index(trigger) + len(trigger):]
                resultado = ejecutar_comando(cmd)
                respuesta = f"Ejecuté el comando. Resultado: {resultado}"
                emocion_actual = astra.emotions.state.emocion
                audio_url = await generar_audio_edge(respuesta, emocion_actual)
                return web.json_response({"respuesta": respuesta, "audio": audio_url})

    # Abrir programas
    if any(w in t for w in ["abre ", "abrir ", "abre el ", "abre la ", "open "]):
        for trigger in ["abre ", "abrir ", "open "]:
            if trigger in t:
                programa = texto[t.index(trigger) + len(trigger):].strip()
                resultado = abrir_programa(programa)
                emocion_actual = astra.emotions.state.emocion
                audio_url = await generar_audio_edge(resultado, emocion_actual)
                return web.json_response({"respuesta": resultado, "audio": audio_url})

    # Buscar archivos
    if any(w in t for w in ["busca ", "buscar ", "encuentra ", "dónde está "]):
        for trigger in ["busca ", "buscar ", "encuentra ", "dónde está "]:
            if trigger in t:
                patron = texto[t.index(trigger) + len(trigger):].strip()
                resultado = buscar_archivos(patron)
                emocion_actual = astra.emotions.state.emocion
                audio_url = await generar_audio_edge(resultado, emocion_actual)
                return web.json_response({"respuesta": resultado, "audio": audio_url})

    # Detectar hora/fecha
    if any(w in t for w in ["hora", "fecha", "día", "qué día"]):
        ahora = datetime.now()
        respuesta = f"Son las {ahora.strftime('%H:%M')} del {ahora.strftime('%d de %B de %Y')}."
        emocion_actual = astra.emotions.state.emocion
        audio_url = await generar_audio_edge(respuesta, emocion_actual)
        return web.json_response({"respuesta": respuesta, "audio": audio_url})

    # Incluir contexto de memoria/aprendizajes para que Astra recuerde
    try:
        memoria_ctx = astra.get_learning_context()
    except Exception:
        memoria_ctx = ""
    
    # Detectar si el usuario dice su nombre (para recordarlo)
    import re
    nombre_patterns = [
        r"(?:me llamo|soy|mi nombre es|dime|llámame)\s+(\w+)",
        r"(?:soy)\s+(\w+)",
    ]
    for pat in nombre_patterns:
        match = re.search(pat, t)
        if match:
            nombre = match.group(1).capitalize()
            if len(nombre) > 2 and nombre.lower() not in ["astra", "un", "una", "el", "la", "tu"]:
                try:
                    astra.memory.remember("nombre_usuario", nombre)
                except Exception:
                    pass
                break
    
    # Incluir nombre del usuario si lo conocemos
    nombre_usuario = None
    try:
        nombre_usuario = astra.memory.recall("nombre_usuario")
    except Exception:
        pass
    
    # Chat normal con el LLM (instrucción mínima para no saturar el contexto)
    texto_final = texto
    contexto_extra = ""
    if nombre_usuario:
        contexto_extra += f"[El usuario se llama {nombre_usuario}. Llámalo por su nombre.]\n"
    if memoria_ctx:
        contexto_extra += f"[Recuerdas: {memoria_ctx}]\n"
    if contexto_extra:
        texto_final = f"{contexto_extra}\n{texto}"
    
    loop = asyncio.get_event_loop()
    try:
        respuesta = await loop.run_in_executor(None, astra.handle, texto_final)
    except Exception as e:
        import traceback
        traceback.print_exc()
        respuesta = f"Disculpa, tuve un problema al procesar eso."

    # Aprendizaje autónomo en background (best-effort, no bloquea respuesta)
    try:
        asyncio.get_event_loop().call_soon(
            lambda: asyncio.ensure_future(_aprender_de_conversacion(texto, respuesta))
        )
    except Exception:
        pass
    
    # Generar audio con voz neuronal — la emoción actual define el tono de voz
    emocion_actual = "neutral"
    try:
        emocion_actual = astra.emotions.state.emocion
    except Exception:
        pass
    audio_url = await generar_audio_edge(respuesta, emocion_actual)
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
    
    emocion = "neutral"
    try:
        emocion = astra.emotions.state.emocion
    except Exception:
        pass
    audio_url = await generar_audio_edge(texto, emocion)
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


async def handle_vision(request):
    """Procesa eventos de la cámara/visión."""
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"respuesta": None, "audio": None})
    
    evento = data.get("evento", "")
    frame = data.get("frame")
    
    respuesta = None
    
    if evento == "camara_activada":
        nombre_usuario = astra.memory.recall("nombre_usuario")
        if nombre_usuario:
            respuesta = f"Hola {nombre_usuario}, ya te veo. ¿En qué te ayudo?"
        else:
            respuesta = "Ya te puedo ver. Oye, no me has dicho tu nombre. ¿Cómo te llamas?"
    
    elif evento == "usuario_volvio":
        # Solo saludar si el usuario estuvo ausente más de 10 minutos
        ultima = astra.memory.recall("ultima_ausencia")
        ahora = datetime.now().timestamp()
        if ultima and (ahora - float(ultima)) > 600:  # 600 seg = 10 min
            nombre_usuario = astra.memory.recall("nombre_usuario")
            if nombre_usuario:
                respuesta = f"Hey {nombre_usuario}, ya regresaste. ¿En qué seguimos?"
            else:
                respuesta = "Ya estás de vuelta. ¿En qué te ayudo?"
        # Si fueron menos de 10 min, no decir nada
    
    elif evento == "usuario_se_fue":
        # Registrar cuándo se fue (para saber si fueron >10 min)
        try:
            astra.memory.remember("ultima_ausencia", str(datetime.now().timestamp()))
        except Exception:
            pass
        respuesta = None
    
    if respuesta:
        emocion_actual = astra.emotions.state.emocion
        audio_url = await generar_audio_edge(respuesta, emocion_actual)
        return web.json_response({"respuesta": respuesta, "audio": audio_url})
    
    return web.json_response({"respuesta": None, "audio": None})


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
    app.router.add_post("/api/vision", handle_vision)
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
