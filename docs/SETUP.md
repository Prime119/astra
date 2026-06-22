# 🚀 Puesta en marcha — Fase 1 (voz + cerebro local)

Esta guía es para tu **PC con Windows**. Aquí Astra empieza a **escucharte, pensar y
responderte hablando**, todo **offline**.

> Esto es la versión de desarrollo (se ejecuta una vez para probar). La app ambiental
> "tipo JARVIS" sin consola llega en fases posteriores.

---

## 1) Instalar el cerebro local (Ollama)

1. Descarga Ollama desde **https://ollama.com/download** e instálalo.
2. Abre una terminal y descarga el modelo (en español, ligero):
   ```
   ollama pull qwen2.5:3b-instruct
   ```
   Si tu PC es potente (16 GB+ RAM o GPU), mejor:
   ```
   ollama pull qwen2.5:7b-instruct
   ```
3. Para programar mejor, opcional:
   ```
   ollama pull qwen2.5-coder:7b
   ```
4. Ollama queda corriendo en segundo plano (http://127.0.0.1:11434). ✅

---

## 2) Instalar Python y las dependencias

1. Instala **Python 3.11+** desde https://www.python.org/downloads/
   (marca "Add Python to PATH" durante la instalación).
2. En la carpeta del proyecto:
   ```
   pip install -r requirements.txt
   ```

---

## 3) Descargar la voz femenina (Piper)

1. Ve a las voces de Piper en español:
   **https://huggingface.co/rhasspy/piper-voices/tree/main/es**
2. Descarga una voz femenina (ej. carpeta `es_MX`), los dos archivos:
   `*.onnx` y `*.onnx.json`.
3. Guárdalos en `astra/voices/` y pon la ruta en `config/astra.config.json`:
   ```json
   "voice": {
     "tts_voice_path": "voices/es_MX-xxxxx-medium.onnx"
   }
   ```

---

## 4) ¡Probar Astra!

Desde la carpeta del proyecto:

```
# Solo ver el estado del sistema
python -m astra.main --status

# Mini-chat de texto (prueba el cerebro)
python -m astra.main

# Conversación por VOZ 🎙️🔊
python -m astra.main --voice
```

En modo voz: Astra te saluda, te escucha, y responde hablando.
Di **"adiós Astra"** para terminar.

> Nota: ejecuta `python` desde la raíz del proyecto con `src` en el PYTHONPATH, o usa los
> lanzadores `.bat` de la carpeta `launchers/` (se afinan en la siguiente fase).

---

## ❓ Si algo falla
- *"No encuentro mi cerebro local"* → revisa que Ollama esté corriendo y el modelo descargado.
- *Sin voz* → revisa que `tts_voice_path` apunte al `.onnx` correcto; si no, Astra mostrará
  el texto en pantalla (degradación graciosa).
- *Micrófono* → revisa permisos de micrófono en Windows.
