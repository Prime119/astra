# 🚀 Puesta en marcha — Conectar el cerebro (Ollama)

Esta guía es para tu **PC con Windows**. Aquí Astra/MEC pasan de "modo básico" a **pensar de
verdad** con un modelo de lenguaje local, todo **offline**.

> Hay dos ediciones (mismo programa): **Astra** (general) y **MEC** (ingeniero de CFE).

---

## 1) Instalar el cerebro local (Ollama)

1. Descarga Ollama desde **https://ollama.com/download** e instálalo.
2. Ábrelo (queda corriendo en segundo plano en `http://127.0.0.1:11434`). ✅
3. Descarga el modelo (en español, ligero):
   ```
   ollama pull qwen2.5:3b-instruct
   ```
   Si tu PC es potente (16 GB+ RAM o GPU), mejor calidad:
   ```
   ollama pull qwen2.5:7b-instruct
   ```
4. Para tareas de programación, opcional:
   ```
   ollama pull qwen2.5-coder:7b
   ```

> 💡 Astra **auto-escala** el modelo según tu hardware (ligera→3b, recomendada→7b, potente→14b).
> Con `--check` (más abajo) te dice exactamente cuál usa y si te falta descargarlo.

---

## 2) Obtener el código de Astra y las dependencias

1. Instala **Python 3.11+** (marca "Add Python to PATH").
2. Clona el repo y entra a la rama del programa:
   ```
   git clone https://github.com/Prime119/astra.git
   cd astra
   git checkout feat/programa-dos-ediciones
   ```
3. (Recomendado) entorno virtual:
   ```
   py -m venv venv
   venv\Scripts\activate
   ```
4. Instala las dependencias mínimas del núcleo:
   ```
   pip install httpx psutil
   ```
   (O todo, incluida la voz: `pip install -r requirements.txt`.)

---

## 3) Verificar que el cerebro está listo

Desde la raíz del proyecto:
```
set PYTHONPATH=src
python -m astra --check
```
- Si dice **"✅ Todo listo"**, ¡a chatear!
- Si falta algo, te muestra el **comando exacto** (`ollama pull ...`).

> En PowerShell usa `$env:PYTHONPATH="src"` en vez de `set PYTHONPATH=src`.

---

## 4) ¡Hablar con Astra / MEC!

```
# Astra (edición general)
python -m astra --full

# MEC (edición CFE, ingeniero profesional)
python -m astra --cfe

# Un solo turno de prueba
python -m astra --cfe --say "¿para qué sirve una subestación?"

# Solo estado del sistema
python -m astra --status
```

- **Astra** te responde con voz femenina (cuando actives la voz) y trato general.
- **MEC** responde como **ingeniero de CFE** (formal, técnico) y se activará con "Oye MEC".

> 🔊 La conversación por voz (`--voice`) y la voz Piper se configuran en una fase posterior;
> por ahora el chat de texto ya usa el cerebro real.

---

## 5) (Opcional) Voz — Piper

1. Descarga una voz de Piper en español:
   **https://huggingface.co/rhasspy/piper-voices/tree/main/es**
2. Guarda los archivos `*.onnx` y `*.onnx.json` en `astra/voices/`.
3. Apunta la ruta en `config/astra.config.json` → `voice.tts_voice_path`.

---

## ❓ Si algo falla
- *"[Modo básico] Mi cerebro completo no está activo"* → Ollama no está corriendo o falta el
  modelo. Corre `python -m astra --check` y sigue las instrucciones.
- *`ModuleNotFoundError: httpx`* → `pip install httpx psutil`.
- *`python` no se reconoce* → usa `py -m astra ...`.
- *No encuentra el módulo `astra`* → asegúrate de tener `PYTHONPATH=src` y de estar en la raíz del repo.
