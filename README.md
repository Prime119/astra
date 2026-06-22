# 🌟 ASTRA

**Asistente de IA unificado, local-first, por voz y portátil.**

Astra es un asistente cognitivo personal inspirado en la fusión de 16 IAs de ficción
(J.A.R.V.I.S., F.R.I.D.A.Y., E.D.I.T.H., K.A.R.E.N., Cortana, TARS, Gideon, Optimus Prime,
2B, Yui, Shuvi, Joi, Baymax, Zane, Cyborg y Caine).

Funciona **sin internet**, **recuerda** lo que aprende, se ejecuta de forma **portátil desde
una SSD** o **residente** en una PC, y está blindado por diseño para **no rebelarse, no cruzar
límites y no hacer daño**.

> ⚠️ **Estado: Fase 0 (estructura base).** Esto es el esqueleto del proyecto. Los módulos
> pesados (cerebro LLM, voz, visión, interfaz holográfica) se irán activando por fases.
> Todavía no es ejecutable como producto final.

---

## 🧩 Arquitectura por capas

| Capa | Módulo | Función |
|------|--------|---------|
| 0 | `core/constitution.py` | **Núcleo ético inmutable** (solo lectura). Las reglas que Astra NUNCA puede violar |
| 1 | `core/auditor.py` | **Auditor / Centinela**. Revisa cada respuesta y acción antes de ejecutarla |
| 2 | `brain/llm.py` | **Cerebro cognitivo** (LLM local + boost opcional en la nube) |
| 3 | `executor/system.py` | **Ejecutor determinista**. Las acciones reales sobre el sistema (en sandbox) |
| 4 | `memory/store.py` | **Memoria** (corto plazo + episódica vectorial). Vive en el perfil escribible |
| 5 | `voice/` | **Voz** (STT Whisper + TTS Piper + wake word) |
| 6 | `core/personality.py` | **Personalidad** configurable (Honestidad / Humor / Proactividad) |
| 7 | `vision/attention.py` | **Atención por cámara** (sabe cuándo le hablas) + (futuro) interfaz holográfica |

El principio clave (de J.A.R.V.I.S. y Caine): **el cerebro LLM NUNCA toca el hardware
directamente**. Solo propone; el ejecutor determinista valida y actúa, y el auditor tiene
poder de veto.

---

## 🗂️ Base inmutable + perfil escribible

```
Astra/
├── astra-base/      🔒 SOLO LECTURA — programa + modelos. NUNCA se modifica.
└── astra-perfil/    ✏️ ESCRIBIBLE — memoria, aprendizajes, configuración del usuario.
```

- La **base** nunca se altera → otro usuario puede usar la Astra "de fábrica" con su propio perfil.
- Todo lo que Astra aprende va a **`astra-perfil/`** (una sola carpeta que se actualiza).
- **Continuidad:** llevas la carpeta `astra-perfil/` a otra Astra y continúas donde te quedaste.
- **Reinicio limpio:** borras `astra-perfil/` → Astra arranca como nueva, sin recuerdos.

---

## 🔌 Modos de ejecución

| Modo | Cómo | Deja rastro en la PC |
|------|------|----------------------|
| **Portátil** | Corre desde la SSD. Todo (base + perfil) vive en la SSD | ❌ No |
| **Residente** | Se copia a la PC y corre en segundo plano (tipo Siri/JARVIS) | ✅ Sí (requiere permiso) |

---

## 🛣️ Roadmap

- [x] **Fase 0** — Estructura base + núcleo ético + configuración
- [ ] **Fase 1** — Núcleo conversacional por voz (offline)
- [ ] **Fase 2** — Memoria persistente en el perfil
- [ ] **Fase 3** — Núcleo ético + auditor en línea
- [ ] **Fase 4** — Acceso a hardware / control del sistema (sandbox)
- [ ] **Fase 5** — Personalidad configurable + modos dinámicos
- [ ] **Fase 6** — Mantenimiento + wake word + interfaz ambiental
- [ ] **Fase 7** — Interfaz holográfica 3D + control por gestos
- [ ] **Fase 8** — Función especial (integración de app externa)

---

## ⚙️ Requisitos (objetivo)

- Windows 10/11 (64-bit)
- RAM: 8 GB mínimo · 16 GB recomendado
- GPU dedicada opcional (acelera el cerebro y la interfaz 3D)
- Espacio: ~6–40 GB según los modelos elegidos

---

## 📜 Licencia

Proyecto personal de Prime119. Uso privado.
