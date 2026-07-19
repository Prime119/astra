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
import re as re_module
import time

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

# Carpeta para cache de audio generado (se limpia al iniciar para usar nueva config de voz)
AUDIO_CACHE = RAIZ / "web" / "static" / "audio"
if AUDIO_CACHE.exists():
    import shutil
    shutil.rmtree(AUDIO_CACHE, ignore_errors=True)
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


# === ESTADO GLOBAL PARA COMPANION MODE Y TAREAS ===
_last_user_activity = time.time()
_proactive_suggestions = []  # Cola de sugerencias proactivas
_scheduled_tasks = []  # Tareas programadas pendientes
_companion_running = False  # Flag para el loop de companion mode


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


def programar_tarea(descripcion: str, minutos: int) -> str:
    """Programa un recordatorio/tarea usando threading.Timer."""
    try:
        def _ejecutar_tarea():
            timestamp = datetime.now().strftime("%H:%M:%S")
            _proactive_suggestions.append({
                "tipo": "recordatorio",
                "mensaje": f"⏰ Recordatorio ({timestamp}): {descripcion}",
                "hora": timestamp
            })
            # Intentar notificación del sistema
            try:
                notificar("Recordatorio - Astra", descripcion)
            except Exception:
                pass

        timer = threading.Timer(minutos * 60, _ejecutar_tarea)
        timer.daemon = True
        timer.start()
        _scheduled_tasks.append({
            "descripcion": descripcion,
            "minutos": minutos,
            "programado": datetime.now().strftime("%H:%M:%S"),
            "timer": timer
        })
        return f"Listo, te recordaré '{descripcion}' en {minutos} minutos."
    except Exception as e:
        return f"Error al programar la tarea: {e}"


def obtener_clipboard() -> str:
    """Lee el contenido del portapapeles."""
    try:
        if platform.system() == "Windows":
            result = subprocess.run(
                ["powershell", "-command", "Get-Clipboard"],
                capture_output=True, text=True, timeout=10
            )
            contenido = result.stdout.strip()
            if contenido:
                return f"Contenido del portapapeles: {contenido[:500]}"
            return "El portapapeles está vacío."
        elif platform.system() == "Linux":
            result = subprocess.run(
                ["xclip", "-selection", "clipboard", "-o"],
                capture_output=True, text=True, timeout=10
            )
            contenido = result.stdout.strip()
            if contenido:
                return f"Contenido del portapapeles: {contenido[:500]}"
            return "El portapapeles está vacío."
        elif platform.system() == "Darwin":
            result = subprocess.run(
                ["pbpaste"], capture_output=True, text=True, timeout=10
            )
            contenido = result.stdout.strip()
            if contenido:
                return f"Contenido del portapapeles: {contenido[:500]}"
            return "El portapapeles está vacío."
        else:
            return "Sistema operativo no soportado para clipboard."
    except Exception as e:
        return f"Error al leer el portapapeles: {e}"


def escribir_clipboard(texto: str) -> str:
    """Escribe texto al portapapeles."""
    try:
        if platform.system() == "Windows":
            process = subprocess.Popen(
                ["powershell", "-command", f"Set-Clipboard -Value '{texto}'"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            process.wait(timeout=10)
            return f"Copié al portapapeles: '{texto[:100]}...'" if len(texto) > 100 else f"Copié al portapapeles: '{texto}'"
        elif platform.system() == "Linux":
            process = subprocess.Popen(
                ["xclip", "-selection", "clipboard"],
                stdin=subprocess.PIPE
            )
            process.communicate(input=texto.encode(), timeout=10)
            return f"Copié al portapapeles: '{texto[:100]}'"
        elif platform.system() == "Darwin":
            process = subprocess.Popen(
                ["pbcopy"], stdin=subprocess.PIPE
            )
            process.communicate(input=texto.encode(), timeout=10)
            return f"Copié al portapapeles: '{texto[:100]}'"
        else:
            return "Sistema operativo no soportado para clipboard."
    except Exception as e:
        return f"Error al escribir en el portapapeles: {e}"


def listar_procesos() -> str:
    """Lista los procesos en ejecución con su uso de recursos."""
    try:
        procesos = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                info = proc.info
                if info['cpu_percent'] and info['cpu_percent'] > 0:
                    procesos.append(info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        # Ordenar por uso de CPU
        procesos.sort(key=lambda x: x.get('cpu_percent', 0), reverse=True)
        top = procesos[:15]
        if not top:
            # Si no hay procesos con CPU > 0, mostrar los de mayor memoria
            for proc in psutil.process_iter(['pid', 'name', 'memory_percent']):
                try:
                    procesos.append(proc.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            procesos.sort(key=lambda x: x.get('memory_percent', 0), reverse=True)
            top = procesos[:15]
        
        lineas = ["Procesos activos (top 15):"]
        for p in top:
            lineas.append(f"  • {p['name']} (PID {p['pid']}) - CPU: {p.get('cpu_percent', 0):.1f}% | RAM: {p.get('memory_percent', 0):.1f}%")
        return "\n".join(lineas)
    except Exception as e:
        return f"Error al listar procesos: {e}"


def matar_proceso(nombre: str) -> str:
    """Mata un proceso por nombre."""
    try:
        killed = 0
        for proc in psutil.process_iter(['name', 'pid']):
            try:
                if nombre.lower() in proc.info['name'].lower():
                    proc.kill()
                    killed += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        if killed > 0:
            return f"Terminé {killed} proceso(s) con nombre '{nombre}'."
        else:
            return f"No encontré ningún proceso con nombre '{nombre}'."
    except Exception as e:
        return f"Error al matar proceso: {e}"


def notificar(titulo: str, mensaje: str) -> str:
    """Muestra una notificación toast del sistema (Windows via PowerShell)."""
    try:
        if platform.system() == "Windows":
            script = f'''
            [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
            $template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
            $textNodes = $template.GetElementsByTagName("text")
            $textNodes.Item(0).AppendChild($template.CreateTextNode("{titulo}")) > $null
            $textNodes.Item(1).AppendChild($template.CreateTextNode("{mensaje}")) > $null
            $toast = [Windows.UI.Notifications.ToastNotification]::new($template)
            [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("Astra").Show($toast)
            '''
            subprocess.Popen(
                ["powershell", "-command", script],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            return f"Notificación enviada: {titulo} - {mensaje}"
        elif platform.system() == "Linux":
            subprocess.Popen(
                ["notify-send", titulo, mensaje],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            return f"Notificación enviada: {titulo} - {mensaje}"
        elif platform.system() == "Darwin":
            subprocess.Popen(
                ["osascript", "-e", f'display notification "{mensaje}" with title "{titulo}"'],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            return f"Notificación enviada: {titulo} - {mensaje}"
        else:
            return "Notificaciones no soportadas en este sistema."
    except Exception as e:
        return f"Error al enviar notificación: {e}"


async def _investigar_para_sim(tema: str):
    """Investiga en internet sobre un tema antes de hacer una simulación (en background)."""
    try:
        await buscar_en_internet(f"cómo funciona {tema} partes componentes", astra)
    except Exception:
        pass


def _limpiar_respuesta(respuesta: str) -> str:
    """Post-procesamiento: elimina saludos repetidos y frases robóticas del modelo."""
    import re
    # Eliminar "¡Hola, nombre!" o "Hola, nombre." al inicio
    respuesta = re.sub(r'^[¡!]?[Hh]ola,?\s*\w+[.!]?\s*', '', respuesta).strip()
    # Eliminar "¿Cómo estás?" al inicio
    respuesta = re.sub(r'^¿?[Cc]ómo\s+est[aá]s\??\s*', '', respuesta).strip()
    # Eliminar "¿En qué puedo ayudarte hoy?" genérico
    respuesta = re.sub(r'^¿?[Ee]n\s+qu[eé]\s+puedo\s+(ayudarte|ser\s+[uú]til|asistirte)\s*(hoy)?\??\s*', '', respuesta).strip()
    # Si quedó vacío después de limpiar, dar respuesta genérica
    if not respuesta or len(respuesta) < 3:
        respuesta = "Aquí estoy. ¿Qué necesitas?"
    # Capitalizar primera letra
    if respuesta[0].islower():
        respuesta = respuesta[0].upper() + respuesta[1:]
    return respuesta


async def buscar_en_internet(query: str, astra_instance) -> str:
    """Busca información en internet y la guarda en la memoria de Astra para aprender.
    Si DuckDuckGo no devuelve resultados, intenta con Wikipedia."""
    try:
        import httpx as hx
        # Usar DuckDuckGo Instant Answer API (gratis, sin API key)
        r = await asyncio.get_event_loop().run_in_executor(
            None, lambda: hx.get(
                "https://api.duckduckgo.com/",
                params={"q": query, "format": "json", "no_html": "1", "skip_disambig": "1"},
                timeout=10.0
            )
        )
        data = r.json()
        
        # Extraer información relevante
        info_parts = []
        if data.get("Abstract"):
            info_parts.append(data["Abstract"])
        if data.get("Answer"):
            info_parts.append(data["Answer"])
        if not info_parts and data.get("RelatedTopics"):
            for topic in data["RelatedTopics"][:3]:
                if isinstance(topic, dict) and topic.get("Text"):
                    info_parts.append(topic["Text"])
        
        # Si DuckDuckGo no devuelve nada, intentar con Wikipedia en español
        if not info_parts:
            try:
                topic_encoded = query.replace(" ", "_")
                wiki_r = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: hx.get(
                        f"https://es.wikipedia.org/api/rest_v1/page/summary/{topic_encoded}",
                        timeout=10.0
                    )
                )
                if wiki_r.status_code == 200:
                    wiki_data = wiki_r.json()
                    if wiki_data.get("extract"):
                        info_parts.append(wiki_data["extract"])
            except Exception:
                pass  # Wikipedia también falló, se reporta sin resultados
        
        if info_parts:
            info = " ".join(info_parts)[:500]
            # GUARDAR EN MEMORIA (aprendizaje de internet)
            try:
                astra_instance.memory.log_episode("internet", f"Búsqueda: {query} | Resultado: {info[:200]}")
                astra_instance.learning._store_or_update("conocimiento", f"Investigó sobre: {query}")
            except Exception:
                pass
            
            # Pedir al LLM que resuma la info para el usuario
            loop = asyncio.get_event_loop()
            respuesta = await loop.run_in_executor(
                None, astra_instance.handle,
                f"[Información encontrada en internet sobre '{query}']: {info}\n\nResume esto de forma clara y breve para el usuario."
            )
            return respuesta
        else:
            return f"Busqué '{query}' pero no encontré información directa. Puedo intentar de otra forma si quieres."
    except Exception as e:
        return f"No pude conectarme a internet para buscar eso. Verifica tu conexión."


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
    "neutral":     {"rate": "+12%", "pitch": "+10Hz"},     # natural, más rápida
    "feliz":       {"rate": "+16%", "pitch": "+20Hz"},     # alegre
    "emocionada":  {"rate": "+20%", "pitch": "+25Hz"},     # energética
    "apasionada":  {"rate": "+16%", "pitch": "+18Hz"},     # entusiasta
    "divertida":   {"rate": "+14%", "pitch": "+22Hz"},     # juguetona
    "curiosa":     {"rate": "+12%", "pitch": "+15Hz"},     # interesada
    "orgullosa":   {"rate": "+10%", "pitch": "+12Hz"},     # segura
    "satisfecha":  {"rate": "+10%", "pitch": "+12Hz"},     # contenta
    "triste":      {"rate": "+5%",  "pitch": "+2Hz"},      # lenta sin ser robótica
    "nostalgica":  {"rate": "+7%",  "pitch": "+5Hz"},      # pausada
    "frustrada":   {"rate": "+16%", "pitch": "+5Hz"},      # rápida
    "enojada":     {"rate": "+18%", "pitch": "+0Hz"},      # rápida, seria
    "impaciente":  {"rate": "+22%", "pitch": "+8Hz"},      # muy rápida
    "preocupada":  {"rate": "+8%",  "pitch": "+5Hz"},      # seria
    "estresada":   {"rate": "+14%", "pitch": "+3Hz"},      # tensa
    "cansada":     {"rate": "+5%",  "pitch": "+5Hz"},      # lenta
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


async def handle_chat_stream(request):
    """Endpoint de chat con streaming SSE (Server-Sent Events).
    Envía la respuesta del LLM palabra por palabra usando StreamResponse."""
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "No entendí el mensaje."}, status=400)
    
    texto = data.get("texto", "").strip()
    if not texto:
        return web.json_response({"error": "Texto vacío."}, status=400)

    # Actualizar actividad del usuario
    global _last_user_activity
    _last_user_activity = time.time()

    # Si el modelo aún está precalentándose, esperar
    if not modelo_listo.is_set():
        modelo_listo.wait(timeout=5.0)

    # Preparar contexto (nombre, memoria)
    try:
        memoria_ctx = astra.get_learning_context()
    except Exception:
        memoria_ctx = ""
    
    nombre_usuario = None
    try:
        nombre_usuario = astra.memory.recall("nombre_usuario")
    except Exception:
        pass
    
    texto_final = texto
    contexto_extra = ""
    if nombre_usuario:
        contexto_extra += f"[El usuario se llama {nombre_usuario}. Llámalo por su nombre.]\n"
    if memoria_ctx:
        contexto_extra += f"[Recuerdas: {memoria_ctx}]\n"
    if contexto_extra:
        texto_final = f"{contexto_extra}\n{texto}"

    # Preparar StreamResponse para SSE
    response = web.StreamResponse(
        status=200,
        reason='OK',
        headers={
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no',
        }
    )
    await response.prepare(request)

    try:
        import httpx as hx
        # Obtener configuración del modelo de Astra
        model_name = astra.brain.model_name if hasattr(astra.brain, 'model_name') else "llama3"
        ollama_url = "http://localhost:11434/api/generate"
        
        # Construir el prompt con el system prompt de Astra
        system_prompt = ""
        try:
            system_prompt = astra.brain.get_system_prompt() if hasattr(astra.brain, 'get_system_prompt') else ""
        except Exception:
            pass

        payload = {
            "model": model_name,
            "prompt": texto_final,
            "stream": True
        }
        if system_prompt:
            payload["system"] = system_prompt

        full_response = ""
        async with hx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", ollama_url, json=payload) as stream:
                async for line in stream.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        chunk_data = json.loads(line)
                        token = chunk_data.get("response", "")
                        if token:
                            full_response += token
                            # Enviar como SSE
                            sse_data = json.dumps({"token": token})
                            await response.write(f"data: {sse_data}\n\n".encode('utf-8'))
                        if chunk_data.get("done", False):
                            break
                    except json.JSONDecodeError:
                        continue

        # Enviar evento final con metadata
        emocion_actual = "neutral"
        try:
            emocion_actual = astra.emotions.state.emocion
        except Exception:
            pass
        
        audio_url = await generar_audio_edge(full_response, emocion_actual)
        final_data = json.dumps({"done": True, "audio": audio_url, "full_response": full_response})
        await response.write(f"data: {final_data}\n\n".encode('utf-8'))

        # Aprendizaje en background
        try:
            asyncio.get_event_loop().call_soon(
                lambda: asyncio.ensure_future(_aprender_de_conversacion(texto, full_response))
            )
        except Exception:
            pass

    except Exception as e:
        error_data = json.dumps({"error": str(e), "done": True})
        await response.write(f"data: {error_data}\n\n".encode('utf-8'))

    await response.write_eof()
    return response


async def handle_chat(request):
    """Endpoint principal de chat con Astra."""
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"respuesta": "No entendí el mensaje. Intenta de nuevo."})
    texto = data.get("texto", "").strip()
    if not texto:
        return web.json_response({"respuesta": ""})

    # Actualizar actividad del usuario para companion mode
    global _last_user_activity
    _last_user_activity = time.time()

    # Si el modelo aún está precalentándose, esperar un poco
    if not modelo_listo.is_set():
        modelo_listo.wait(timeout=5.0)

    # Detectar si pide info del sistema
    t = texto.lower()
    
    # === SIMULACIONES/HOLOGRAMAS 3D ===
    sim_keywords = ["simulación", "simulacion", "simula", "holograma", "hologram", "3d"]
    sim_acciones = ["crea", "genera", "haz", "muestra", "hazme", "créame", "creame", "simula", "pon"]
    tiene_sim = any(w in t for w in sim_keywords)
    tiene_acc = any(w in t for w in sim_acciones)
    
    if tiene_sim and tiene_acc:
        # Investigar en internet ANTES de crear la simulación (para aprender)
        try:
            tema_buscar = texto.replace("crea", "").replace("genera", "").replace("haz", "").replace("simula", "").replace("simulación", "").replace("holograma", "").strip()
            if tema_buscar and len(tema_buscar) > 3:
                asyncio.ensure_future(_investigar_para_sim(tema_buscar))
        except Exception:
            pass
        
        # Determinar tipo por contenido (templates de alta calidad)
        sim_type = "particulas"
        if any(w in t for w in ["agujero negro", "black hole", "singularidad"]):
            sim_type = "agujero_negro"
        elif any(w in t for w in ["sistema solar", "planeta", "sol", "tierra", "luna", "órbita"]):
            sim_type = "sistema_solar"
        elif any(w in t for w in ["galaxia", "vía láctea", "espiral"]):
            sim_type = "galaxia"
        elif any(w in t for w in ["átomo", "atomo", "molécula", "molecula", "electrón", "adn", "dna"]):
            sim_type = "atomo"
        elif any(w in t for w in ["universo", "cosmos", "nebulosa", "big bang", "estrellas"]):
            sim_type = "universo"
        elif any(w in t for w in ["cubo", "esfera", "geometr", "pirámide", "forma", "toroide"]):
            sim_type = "geometria"
        elif any(w in t for w in ["onda", "wave", "frecuencia", "vibración", "cuerdas", "string"]):
            sim_type = "ondas"
        elif any(w in t for w in ["campo", "magnético", "eléctrico", "fuerza", "gravedad"]):
            sim_type = "campo"
        elif any(w in t for w in ["tornado", "vórtice", "vortice", "espiral", "remolino"]):
            sim_type = "vortice"
        elif any(w in t for w in ["explosión", "explosion", "supernova", "big bang"]):
            sim_type = "explosion"
        # === INGENIERÍA ===
        elif any(w in t for w in ["motor", "pistón", "piston", "cilindro", "combustión"]):
            sim_type = "motor"
        elif any(w in t for w in ["engranaje", "gear", "mecanismo", "reloj"]):
            sim_type = "engranajes"
        elif any(w in t for w in ["circuito", "eléctrico", "electrico", "corriente", "resistencia"]):
            sim_type = "circuito"
        elif any(w in t for w in ["puente", "estructura", "viga", "columna", "edificio"]):
            sim_type = "puente"
        elif any(w in t for w in ["fluido", "agua", "líquido", "liquido", "hidráulica"]):
            sim_type = "fluido"
        elif any(w in t for w in ["péndulo", "pendulo", "oscilación", "oscilacion"]):
            sim_type = "pendulo"
        elif any(w in t for w in ["cohete", "propulsión", "nave", "espacial", "lanzamiento"]):
            sim_type = "cohete"
        elif any(w in t for w in ["adn", "dna", "célula", "celula", "biología", "genética"]):
            sim_type = "adn"
        elif any(w in t for w in ["red neuronal", "neural", "cerebro", "neurona", "sinapsis"]):
            sim_type = "red_neuronal"
        elif any(w in t for w in ["turbina", "hélice", "helice", "ventilador", "rotor"]):
            sim_type = "turbina"
        
        respuesta = "Listo, ahí está tu simulación."
        emocion_actual = astra.emotions.state.emocion
        audio_url = await generar_audio_edge(respuesta, emocion_actual)
        return web.json_response({
            "respuesta": respuesta,
            "audio": audio_url,
            "simulacion": sim_type
        })

    # === BÚSQUEDA EN INTERNET ===
    busca_triggers = ["busca en internet", "investiga en la web", "googlea", "busca en la red",
                      "busca en línea", "busca en linea", "qué dice internet sobre",
                      "busca información sobre", "busca info sobre", "search"]
    if any(trigger in t for trigger in busca_triggers):
        # Extraer el tema de búsqueda
        query = texto
        for trigger in busca_triggers:
            if trigger in t:
                idx = t.index(trigger) + len(trigger)
                query = texto[idx:].strip()
                break
        if query:
            resultado = await buscar_en_internet(query, astra)
            emocion_actual = astra.emotions.state.emocion
            audio_url = await generar_audio_edge(resultado, emocion_actual)
            return web.json_response({"respuesta": resultado, "audio": audio_url})

    # === CLIPBOARD / PORTAPAPELES ===
    if any(w in t for w in ["clipboard", "portapapeles"]):
        if any(w in t for w in ["copia", "escribe", "pon", "guarda"]):
            # Extraer texto a copiar
            contenido_a_copiar = texto
            for trigger in ["copia ", "escribe ", "pon ", "guarda "]:
                if trigger in t:
                    idx = t.index(trigger) + len(trigger)
                    contenido_a_copiar = texto[idx:].strip()
                    # Limpiar prefijos como "en el clipboard" etc
                    for remove in ["en el clipboard", "en el portapapeles", "al clipboard", "al portapapeles"]:
                        contenido_a_copiar = contenido_a_copiar.replace(remove, "").strip()
                    break
            respuesta = escribir_clipboard(contenido_a_copiar)
        else:
            respuesta = obtener_clipboard()
        emocion_actual = astra.emotions.state.emocion
        audio_url = await generar_audio_edge(respuesta, emocion_actual)
        return web.json_response({"respuesta": respuesta, "audio": audio_url})

    # === PROCESOS ===
    if any(w in t for w in ["mata el proceso", "mata proceso", "kill proceso", "termina proceso", "cierra proceso"]):
        # Extraer nombre del proceso
        nombre_proc = ""
        for trigger in ["mata el proceso ", "mata proceso ", "kill proceso ", "termina proceso ", "cierra proceso "]:
            if trigger in t:
                nombre_proc = texto[t.index(trigger) + len(trigger):].strip()
                break
        if nombre_proc:
            respuesta = matar_proceso(nombre_proc)
        else:
            respuesta = "¿Qué proceso quieres que termine? Dime el nombre."
        emocion_actual = astra.emotions.state.emocion
        audio_url = await generar_audio_edge(respuesta, emocion_actual)
        return web.json_response({"respuesta": respuesta, "audio": audio_url})

    if "procesos" in t and any(w in t for w in ["lista", "muestra", "ver", "cuáles", "cuales", "qué", "que"]):
        respuesta = listar_procesos()
        emocion_actual = astra.emotions.state.emocion
        audio_url = await generar_audio_edge(respuesta, emocion_actual)
        return web.json_response({"respuesta": respuesta, "audio": audio_url})

    # === RECORDATORIOS Y NOTIFICACIONES ===
    recuerdame_match = re_module.search(r"recu[eé]rdame\s+(?:en\s+)?(\d+)\s*minutos?", t)
    if recuerdame_match:
        minutos = int(recuerdame_match.group(1))
        # Extraer descripción (lo que viene después de "minutos" o antes de "en X min")
        desc = texto
        # Intentar extraer la descripción limpia
        desc_match = re_module.search(r"recu[eé]rdame\s+(?:en\s+\d+\s*minutos?\s+(?:que\s+)?)?(.+)", texto, re_module.IGNORECASE)
        if desc_match:
            desc = desc_match.group(1).strip()
            # Limpiar si la desc empieza con "que"
            if desc.lower().startswith("que "):
                desc = desc[4:]
        else:
            desc_match2 = re_module.search(r"(.+?)\s+en\s+\d+\s*minutos?", texto, re_module.IGNORECASE)
            if desc_match2:
                desc = desc_match2.group(1).replace("recuérdame", "").replace("recuerdame", "").strip()
        if not desc or desc == texto:
            desc = "Recordatorio programado"
        respuesta = programar_tarea(desc, minutos)
        emocion_actual = astra.emotions.state.emocion
        audio_url = await generar_audio_edge(respuesta, emocion_actual)
        return web.json_response({"respuesta": respuesta, "audio": audio_url})

    # Detección de "recuérdame" o "notifícame" sin tiempo específico → preguntar
    if any(w in t for w in ["recuérdame", "recuerdame", "notifícame", "notificame"]):
        # Intentar extraer si hay tiempo en formato diferente
        tiempo_match = re_module.search(r"(\d+)\s*(?:min|minutos?|hrs?|horas?)", t)
        if tiempo_match:
            minutos = int(tiempo_match.group(1))
            if "hora" in tiempo_match.group(0) or "hr" in tiempo_match.group(0):
                minutos = minutos * 60
            desc = re_module.sub(r"\d+\s*(?:min|minutos?|hrs?|horas?)", "", texto)
            for remove in ["recuérdame", "recuerdame", "notifícame", "notificame", "en", "que"]:
                desc = desc.replace(remove, "")
            desc = desc.strip() or "Recordatorio"
            respuesta = programar_tarea(desc, minutos)
        else:
            respuesta = "¿En cuántos minutos quieres que te recuerde? Dime algo como 'recuérdame en 5 minutos que...'."
        emocion_actual = astra.emotions.state.emocion
        audio_url = await generar_audio_edge(respuesta, emocion_actual)
        return web.json_response({"respuesta": respuesta, "audio": audio_url})

    # === CREAR ARCHIVOS/DOCUMENTOS ===
    crear_file_triggers = ["crea un archivo", "crea un documento", "genera un archivo",
                           "escribe un archivo", "hazme un documento", "crea un txt",
                           "crea un pdf", "genera un documento", "crea una nota",
                           "escríbeme", "escribeme", "redacta", "genera un reporte",
                           "crea un reporte", "haz un ensayo", "crea un ensayo",
                           "genera un contrato", "crea una carta", "haz un resumen",
                           "crea un guión", "crea un guion", "escribe un código",
                           "crea un script", "genera un código", "hazme una lista",
                           "crea una presentación", "genera una tabla"]
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

    # POST-PROCESAMIENTO: eliminar saludos repetidos que el modelo insiste en poner
    respuesta = _limpiar_respuesta(respuesta)

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


async def handle_proactive(request):
    """Devuelve sugerencias proactivas pendientes del companion mode."""
    global _proactive_suggestions
    if _proactive_suggestions:
        sugerencias = list(_proactive_suggestions)
        _proactive_suggestions.clear()
        return web.json_response({"sugerencias": sugerencias, "pendientes": len(sugerencias)})
    return web.json_response({"sugerencias": [], "pendientes": 0})


async def handle_export_training(request):
    """Exporta todas las conversaciones como JSONL para fine-tuning.
    Formato: {"messages": [{"role":"system","content":"..."}, {"role":"user","content":"..."}, {"role":"assistant","content":"..."}]}"""
    try:
        # Obtener historial de conversaciones de la memoria de Astra
        conversaciones = []
        
        # Intentar obtener episodios de la memoria
        try:
            episodes = astra.memory.get_episodes() if hasattr(astra.memory, 'get_episodes') else []
        except Exception:
            episodes = []
        
        # Intentar obtener historial del chat
        try:
            history = astra.memory.get_history() if hasattr(astra.memory, 'get_history') else []
        except Exception:
            history = []
        
        # System prompt de Astra para fine-tuning
        system_prompt = "Eres Astra, una asistente AI personal inteligente, empática y proactiva. Ayudas con tareas del sistema, respuestas creativas y conversación natural."
        try:
            if hasattr(astra.brain, 'get_system_prompt'):
                system_prompt = astra.brain.get_system_prompt()
        except Exception:
            pass

        # Formatear episodios como datos de entrenamiento
        for ep in episodes:
            if isinstance(ep, dict) and ep.get("user") and ep.get("assistant"):
                entry = {
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": str(ep["user"])},
                        {"role": "assistant", "content": str(ep["assistant"])}
                    ]
                }
                conversaciones.append(entry)
        
        # Formatear historial como datos de entrenamiento
        for i in range(0, len(history) - 1, 2):
            if i + 1 < len(history):
                user_msg = history[i] if isinstance(history[i], str) else str(history[i].get("content", ""))
                asst_msg = history[i+1] if isinstance(history[i+1], str) else str(history[i+1].get("content", ""))
                if user_msg and asst_msg:
                    entry = {
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_msg},
                            {"role": "assistant", "content": asst_msg}
                        ]
                    }
                    conversaciones.append(entry)

        # Generar JSONL
        jsonl_content = "\n".join(json.dumps(conv, ensure_ascii=False) for conv in conversaciones)
        
        return web.Response(
            text=jsonl_content,
            content_type="application/jsonl",
            headers={
                "Content-Disposition": f"attachment; filename=astra_training_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
            }
        )
    except Exception as e:
        return web.json_response({"error": f"Error al exportar datos de entrenamiento: {e}"}, status=500)


# === COMPANION MODE (Background Task) ===
async def _companion_mode_loop(app):
    """Background task que revisa cada 60 segundos si el usuario ha estado idle.
    Si lleva más de 5 minutos sin interactuar, genera una sugerencia proactiva."""
    global _companion_running
    _companion_running = True
    
    while _companion_running:
        await asyncio.sleep(60)  # Revisar cada 60 segundos
        
        try:
            tiempo_idle = time.time() - _last_user_activity
            # Si el usuario lleva más de 5 minutos (300 seg) sin interactuar
            if tiempo_idle > 300:
                # No generar más de una sugerencia por período de idle
                if len(_proactive_suggestions) < 3:
                    # Generar sugerencia contextual
                    try:
                        info = obtener_info_sistema()
                        sugerencia = None
                        
                        # Sugerencias basadas en estado del sistema
                        if info["ram_pct"] > 85:
                            sugerencia = f"Noté que tu RAM está al {info['ram_pct']}%. ¿Quieres que te muestre qué procesos consumen más memoria?"
                        elif info["cpu_uso"] > 80:
                            sugerencia = f"Tu CPU está al {info['cpu_uso']}%. Puedo ayudarte a identificar qué la está usando tanto."
                        elif info["disco_pct"] > 90:
                            sugerencia = f"Tu disco está al {info['disco_pct']}% de capacidad. ¿Te ayudo a buscar archivos grandes?"
                        else:
                            # Sugerencia genérica amigable
                            hora = datetime.now().hour
                            if hora >= 22 or hora < 6:
                                sugerencia = "Ya es tarde. ¿Necesitas algo más antes de descansar?"
                            elif hora >= 12 and hora <= 14:
                                sugerencia = "Es hora de comer. ¿Necesitas algo antes de tu break?"
                            else:
                                sugerencia = "Llevo un rato sin saber de ti. ¿Todo bien? Aquí estoy si necesitas algo."
                        
                        if sugerencia:
                            _proactive_suggestions.append({
                                "tipo": "companion",
                                "mensaje": sugerencia,
                                "hora": datetime.now().strftime("%H:%M:%S"),
                                "idle_minutos": round(tiempo_idle / 60, 1)
                            })
                    except Exception:
                        pass
        except Exception:
            pass


async def _start_companion(app):
    """Inicia el companion mode como tarea de fondo."""
    app['companion_task'] = asyncio.ensure_future(_companion_mode_loop(app))


async def _stop_companion(app):
    """Detiene el companion mode."""
    global _companion_running
    _companion_running = False
    task = app.get('companion_task')
    if task:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


# === AUTO-INVESTIGACIÓN (Astra aprende sola en segundo plano) ===
_auto_learn_running = False
_TEMAS_AUTO_APRENDIZAJE = [
    "cómo funciona un motor de combustión interna",
    "qué es una red neuronal artificial",
    "cómo funciona la gravedad",
    "estructura de una célula humana",
    "cómo funciona un reactor nuclear",
    "principios de aerodinámica",
    "cómo funciona la memoria humana",
    "qué es la teoría de cuerdas",
    "cómo funciona un procesador de computadora",
    "principios de la mecánica cuántica",
    "cómo se forma una estrella",
    "funcionamiento de un circuito eléctrico",
    "cómo funciona internet",
    "principios de inteligencia artificial",
    "cómo funciona el ADN",
]

async def _auto_learn_loop(app):
    """Background task: Astra investiga y aprende por su cuenta cuando está idle."""
    global _auto_learn_running
    _auto_learn_running = True
    tema_idx = 0
    
    while _auto_learn_running:
        # Esperar 10 minutos entre investigaciones
        await asyncio.sleep(600)
        
        try:
            # Solo investigar si el usuario lleva MÁS de 10 minutos sin interactuar
            tiempo_idle = time.time() - _last_user_activity
            if tiempo_idle < 600:
                continue  # Usuario activo, no molestar
            
            # Elegir tema
            tema = _TEMAS_AUTO_APRENDIZAJE[tema_idx % len(_TEMAS_AUTO_APRENDIZAJE)]
            tema_idx += 1
            
            print(f"   🧠 Auto-aprendizaje: investigando '{tema}'...")
            
            # Buscar en internet
            try:
                resultado = await buscar_en_internet(tema, astra)
                if resultado and "no encontré" not in resultado.lower():
                    # Guardar el conocimiento adquirido
                    try:
                        astra.memory.log_episode("auto_aprendizaje", f"Investigué: {tema}")
                    except Exception:
                        pass
                    print(f"   ✅ Aprendido sobre: {tema}")
                else:
                    print(f"   ⚠️ No encontré info sobre: {tema}")
            except Exception:
                pass  # Si falla internet, seguir
                
        except Exception:
            pass


async def _start_auto_learn(app):
    app['auto_learn_task'] = asyncio.ensure_future(_auto_learn_loop(app))

async def _stop_auto_learn(app):
    global _auto_learn_running
    _auto_learn_running = False
    task = app.get('auto_learn_task')
    if task:
        task.cancel()
        try: await task
        except asyncio.CancelledError: pass


# === APP ===
async def on_startup(app):
    # Solo abrir navegador si NO estamos en modo desktop
    if os.environ.get("ASTRA_MODE") != "desktop":
        loop = asyncio.get_event_loop()
        loop.call_later(1.5, lambda: webbrowser.open("http://localhost:3000"))


def main():
    app = web.Application()
    app.on_startup.append(on_startup)
    app.on_startup.append(_start_companion)
    app.on_startup.append(_start_auto_learn)
    app.on_cleanup.append(_stop_companion)
    app.on_cleanup.append(_stop_auto_learn)
    app.router.add_get("/", handle_index)
    app.router.add_get("/static/{name}", handle_static)
    app.router.add_get("/static/audio/{name}", handle_audio_static)
    app.router.add_post("/api/chat", handle_chat)
    app.router.add_post("/api/chat/stream", handle_chat_stream)
    app.router.add_post("/api/tts", handle_tts)
    app.router.add_post("/api/vision", handle_vision)
    app.router.add_get("/api/status", handle_status)
    app.router.add_get("/api/memory", handle_memory)
    app.router.add_get("/api/proactive", handle_proactive)
    app.router.add_get("/api/export/training", handle_export_training)

    print("=" * 50)
    print("  🌟 ASTRA — Interfaz Web JARVIS")
    print(f"  Voz: {'edge-tts neuronal (' + VOZ_EDGE + ')' if EDGE_TTS_DISPONIBLE else 'navegador (básica)'}")
    print("  Abriendo en http://localhost:3000")
    print("  Nuevas capacidades: Streaming, Companion Mode, PC Control")
    print("  Presiona Ctrl+C para detener")
    print("=" * 50)

    web.run_app(app, host="0.0.0.0", port=3000, print=None)


if __name__ == "__main__":
    main()
