# ASTRA — Ediciones (Full y CFE)

ASTRA se distribuye en **dos ediciones** construidas sobre **un único núcleo de código**. La
diferencia entre ambas es **solo de configuración** (perfiles de edición), no de código duplicado.

> 🔒 **Importante:** el **núcleo ético inmutable** (`config/ethics_core.md`) está presente e intacto
> en **ambas** ediciones. "Full / sin límites" se refiere a **capacidades de funciones**, nunca a
> quitar la ética: eso es justamente lo que define y protege a ASTRA.

---

## 🟦 ASTRA Full
- **Para qué:** asistente cognitivo personal de **propósito general**, con **todas las capacidades
  de función habilitadas**.
- **Persona:** general.
- **Módulo Falcon (OSINT/CFE):** ❌ **no incluido**.
- **Conocimiento:** general (abierto).

## 🟩 ASTRA CFE
- **Para qué:** uso **específico en el área de CFE**. Actúa como **ingeniera profesional de CFE**
  (generación, transmisión/distribución, subestaciones, normativa, seguridad eléctrica…).
- **Persona:** `ingeniero_cfe` (formal, técnica, precisa, pero humana).
- **Capacidades limitadas:** conocimiento general **enfocado a CFE/energía** (`general_knowledge: false`,
  `domain_focus: cfe_energia`).
- **Módulo Falcon (infraestructura CFE en México):** ✅ **incluido** (latente y bajo autenticación).

### Comparativa de capacidades
| Capacidad | Full | CFE |
|---|:---:|:---:|
| text_chat | ✅ | ✅ |
| general_knowledge | ✅ | ❌ (enfoque CFE/energía) |
| code_assistant | ✅ | ✅ |
| voice | ✅ | ✅ |
| vision_attention | ✅ | ✅ |
| face_recognition | ✅ | ✅ |
| emotion_recognition | ✅ | ✅ |
| holomesa (3D) | ✅ | ✅ |
| system_automation | ✅ | ✅ |
| web_access | ✅ | ✅ |
| cloud_boost | ❌ (opt-in) | ❌ (opt-in) |
| **intelligence_falcon** | ❌ | ✅ |

> Las dos ediciones mantienen **perfiles de memoria separados** (`astra-perfil-full/` y
> `astra-perfil-cfe/`), para que su aprendizaje y datos **no se mezclen**.

---

## ▶️ Cómo ejecutar

Desde la raíz del repo (con el código en `src/`):

```bash
# Edición Full (por defecto)
PYTHONPATH=src python3 -m astra

# Edición CFE
PYTHONPATH=src python3 -m astra --cfe

# Solo ver el estado del sistema (sin chatear)
PYTHONPATH=src python3 -m astra --cfe --status

# Un solo turno (no interactivo, útil para pruebas)
PYTHONPATH=src python3 -m astra --full --say "hola Astra"

# Conversación por voz (requiere micrófono + dependencias de voz)
PYTHONPATH=src python3 -m astra --voice
```

Selección de edición (cualquiera de estas):
- `--full` / `--cfe`
- `--edition full` / `--edition cfe`
- variable de entorno `ASTRA_EDITION=cfe`

> 🧠 **Cerebro local:** para razonamiento completo necesita **Ollama** corriendo y el modelo
> descargado (auto-escala por hardware: `qwen2.5:3b/7b/14b`). **Sin Ollama**, ASTRA **degrada con
> honestidad** (modo básico): el núcleo de seguridad y la memoria siguen operativos.

---

## 🧩 Cómo está construido (un núcleo, dos perfiles)

```
config/
  astra.config.json        # configuración BASE (compartida)
  editions/
    full.json              # overlay de la edición Full
    cfe.json               # overlay de la edición CFE  (persona + Falcon + límites)
```

`config.py` carga la base y **fusiona encima** (`_deep_merge`) el overlay de la edición elegida.
Así, añadir una futura edición es solo crear otro `editions/<id>.json`.

### Pipeline de seguridad (Motor Dual)
```
entrada
 → verificación de integridad del núcleo (Zero-Trust; parálisis si fue alterado)
 → Code-Switching (detecta estrés → modo confort/copiloto/crisis)
 → AUDITOR revisa la ENTRADA  (BLOCK / CONFIRM / SAFE)
 → CEREBRO (Módulo A) propone
 → AUDITOR revisa la SALIDA   (Módulo B, anti-gaslighting)
 → responde / confirma → memoria registra (con peso emocional)
```

### Verificado (sin hardware especial)
- ✅ Arranque de ambas ediciones con capacidades y persona correctas.
- ✅ Bloqueo de **jailbreak** y de **sabotaje a infraestructura** (relevante para CFE).
- ✅ **Code-Switching** (crisis / confort / copiloto).
- ✅ **Confirmación human-in-the-loop** multi-turno.
- ✅ **Parálisis preventiva** al alterar el núcleo ético (Zero-Trust).

---

## ⏳ Qué es real hoy vs. qué llega después

| Componente | Estado |
|---|---|
| Núcleo ético + auditor (entrada/salida) + 3 preguntas | ✅ funcional |
| Ediciones Full/CFE + capacidades + persona | ✅ funcional |
| Personalidad (diales, sarcasmo J.A.R.V.I.S., Code-Switching) | ✅ funcional |
| Memoria SQLite (corto plazo + episódica con peso emocional) | ✅ funcional |
| Cerebro local (Ollama) con degradación honesta | ✅ funcional (requiere Ollama para razonar) |
| Voz (STT/TTS) | 🟡 contrato (Fase 1/5) |
| Visión / atención / rostro / emoción | 🟡 contrato (Fases 5/7) |
| Ejecutor real + automatización de apps | 🟡 dry-run (Fase 3/4) |
| Copy-on-Write + servicio en 2º plano | 🟡 config/diseño (Fase 2/3) |
| Holomesa 3D + gestos | ❌ (Fase 7) |
| Módulo Falcon (infraestructura CFE) | 🟡 config/diseño (Fase 6/7) |

> Roadmap completo en `docs/unification/00-SINTESIS-ASTRA.md` y `17`/`18`.
