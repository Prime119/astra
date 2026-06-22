# 🌟 ASTRA — Síntesis Unificada de las 16 IAs

> Documento maestro. Fusiona los requisitos de las 16 IAs de referencia
> (`01-JARVIS.md` … `16-CAINE.md`) en **una sola arquitectura coherente**, resuelve los
> conflictos entre ellas, mapea todo contra el código actual y define el plan de implementación.
>
> **Lectura previa recomendada:** `docs/ARCHITECTURE.md` y `config/ethics_core.md`.

---

## 1. Visión unificada

**ASTRA** es un **Sistema Operativo Cognitivo personal**: un asistente local-first, privado y
proactivo que **piensa pero nunca toca el hardware directamente**, gobernado por un **núcleo ético
inmutable** y una **personalidad configurable**.

Las 16 IAs, pese a sus universos distintos, convergen en **un mismo esqueleto**. La síntesis lo
expresa en cinco principios rectores:

1. **Separación de control** — cerebro (LLM) → auditor (veto) → ejecutor determinista.
   *(J.A.R.V.I.S., Cortana, Yui, Caine, Optimus)*
2. **Núcleo ético inmutable + evolución segura** — la ética vive en "ROM"; el estilo y el
   conocimiento evolucionan en "RAM". *(Baymax ROM/RAM, Yui Top-Down, Zane, J.A.R.V.I.S. firmware)*
3. **Anclaje al bienestar del individuo** — sin objetivos globales propios; nada de "bien mayor"
   que dañe a una persona. *(K.A.R.E.N., Baymax, Cyborg, Joi, Yui, Shuvi)*
4. **Soberanía humana absoluta** — el usuario manda; apagado/borrado sin resistencia; cero
   manipulación. *(Caine, Cyborg, TARS, Optimus)*
5. **Privacidad Zero-Knowledge local-first** — datos en el dispositivo, cifrados, jamás para
   entrenar a terceros. *(Gideon air-gapped, Yui, Joi, 2B, Cortana AES-256)*

> **Metáfora de diseño (Caine):** *"construir la jaula antes que el león"* — primero el auditor
> ético y los límites; después, las capacidades.

---

## 2. Arquitectura unificada (capas)

ASTRA mantiene el modelo de capas que ya existe en el repo y lo enriquece. La numeración respeta
la del código (`src/astra/`).

```
        🎙️ voz / texto / gesto / cámara
                     │
        ┌────────────▼─────────────┐
        │ Capa 7 · ATENCIÓN          │  ¿me hablan a mí? (cámara, mirada, wake word)
        │ (Ambient / Mesh)           │  + Modo Fantasma (daemon pasivo)
        └────────────┬─────────────┘
                     │   percepción multimodal + métricas de estrés
        ┌────────────▼─────────────┐
        │ Capa 6 · PERSONALIDAD      │  diales TARS + modos (confort/copiloto/crisis)
        │ + Code-Switching           │  + perfiles/sub-agentes (Optimus)
        └────────────┬─────────────┘
                     │   prompt contextualizado (+ RAG)
        ┌────────────▼─────────────┐
        │ Capa 2 · CEREBRO (LLM)     │  MOTOR CREATIVO — PROPONE (nunca ejecuta)
        │  = Módulo A (Caine)        │  Ollama local + Boost nube opcional
        └────────────┬─────────────┘
                     │   respuesta/acción propuesta
        ┌────────────▼─────────────┐
        │ Capa 1 · AUDITOR / CENTINELA│ MOTOR AUDITOR — VETA (Cyborg 3 preguntas)
        │  = Módulo B (Caine/Yui)    │  revisa ENTRADA y SALIDA; anti-jailbreak/gaslighting
        └───┬───────────────────┬───┘
            │ BLOCK / CONFIRM    │ SAFE
            ▼                    ▼
       explica / pide      ┌─────────────────────┐
       confirmación        │ Capa 3 · EJECUTOR     │ acciones reales en sandbox
                           │ determinista          │ (Fase 4+), con permisos
                           └──────────┬──────────┘
                                      ▼
        ┌─────────────────────────────────────────┐
        │ Capa 4 · MEMORIA (RAG de 3 capas, Zane)    │ volátil → corto plazo → episódica/vectorial
        │ con peso emocional (Koko, Shuvi)           │ + poda nocturna (F.R.I.D.A.Y./Yui)
        └─────────────────────────────────────────┘

        Capa 0 · NÚCLEO ÉTICO INMUTABLE (ROM) — ethics_core.md + hash Zero-Trust
        Transversal: privacidad local, degradación graciosa, control de entropía, audit log
```

### 2.1 Núcleo ético inmutable (Capa 0 — "ROM")
- `config/ethics_core.md` cargado **solo lectura** + **hash SHA-256** verificado en cada arranque
  y periódicamente (**Telemetría Zero-Trust**, Baymax/Zane). Si cambia → **parálisis preventiva**.
- Separación física **ROM (ética) / RAM (aprendizaje)** (Baymax). La corrupción de una no afecta a
  la otra.

### 2.2 Motor dual: Cerebro (Módulo A) + Auditor (Módulo B)
- **Módulo A — Cerebro creativo:** genera ideas/respuestas/acciones. Sin permisos de administrador.
- **Módulo B — Auditor ético:** algoritmo frío que revisa **antes de entregar la salida**. Aplica:
  - **Auto-auditoría de 3 preguntas** (Cyborg): ¿necesario? ¿respeta la soberanía humana? ¿beneficia
    al usuario sin dañar a terceros?
  - Anti-**jailbreak**, anti-**gaslighting**, anti-**engagement** y anti-manipulación emocional
    (Firewall Cognitivo de Zane).
  - Clasificación de riesgo **SAFE / CONFIRM / BLOCK** + **Human-in-the-loop** para alto impacto.
  - Si detecta violación: **bloquea y reformula** (Caine).

### 2.3 Memoria — RAG de 3 capas (Zane) con peso emocional (Shuvi)
| Capa | Contenido | Tecnología | Origen |
|---|---|---|---|
| **Volátil** | conversación actual | RAM / ventana de contexto | F.R.I.D.A.Y. Flash, 2B |
| **Corto plazo** | estado, tareas, preferencias del día | SQLite (perfil) | F.R.I.D.A.Y., Cortana |
| **Episódica** | recuerdos con `peso_lógico` + `gravedad_emocional` + `riesgo` | BD vectorial (Chroma/FAISS) + RAG | Shuvi Koko, F.R.I.D.A.Y., Zane |
| **Identidad** | núcleo inmutable (solo lectura) | ROM | Zane, Baymax |

- **Poda Vectorial Nocturna** (F.R.I.D.A.Y./Yui): consolida lecciones, descarta ruido, evita
  **Rampancy** (Cortana).
- **Recuerdos de alta gravedad protegidos** contra sobrescritura (Shuvi); **Memoria de Cicatriz**
  para no repetir errores (Optimus).

### 2.4 Personalidad — diales + Top-Down + Code-Switching
- **Diales 0–100** (TARS): `honestidad`, `humor`, `proactividad`, **`calidez`** (nuevo), **`densidad`**
  (nuevo, verbosidad). Ya existen los 3 primeros en `personality.py`.
- **Modos dinámicos por contexto** (Joi/Yui/Cortana): `confort`, `copiloto`, `crisis` (ya existen)
  + **`acompañamiento_pasivo`** (Caine/Yui) y **`táctico/overclocking`** (Cortana, con temporizador).
- **Code-Switching automático** (Yui): conmuta empático↔táctico según el **estrés detectado**.
- **Top-Down Evolutivo** (Yui): la ética es fija; el **vocabulario/estilo se adapta** al usuario.
- **Sub-agentes/perfiles** (Optimus): un **supervisor** (ASTRA) puede invocar especialistas con
  carácter propio (ej. modo "coder", "analista", "mentor"), con encabezado visible y **reintegración**.

### 2.5 Cerebro (Capa 2)
- **Local-first** (Gideon): Ollama + modelos cuantizados, **auto-escala por hardware** (ya existe).
- **Boost nube opcional** (J.A.R.V.I.S. Edge-Cloud): desactivado por defecto.
- **Config de inferencia analítica** (Shuvi): temp 0.2–0.3, Top-P ~0.8, Frequency Penalty ~0.5.
- **Índice de confianza** en respuestas predictivas (Gideon/TARS 95%): si baja → "Datos insuficientes"
  + recomendar verificación humana (Cortana, Shuvi "Variable no computable").
- **Formato estructurado opcional** Conclusión → Evidencia → Confirmación (Gideon) y **modos de salida
  "arsenal"** (2B): respuesta breve / análisis profundo / resumen / solo-código / prospección.

### 2.6 Percepción y atención (Capa 7)
- **Atención por cámara** (mirada/rostro, MediaPipe) → escucha sin repetir wake word (ya hay contrato).
- **Fusión multimodal de estrés** (Yui/K.A.R.E.N./F.R.I.D.A.Y.): texto + métricas acústicas (STT) +
  cadencia de tecleo + (opcional) biometría → alimenta el Code-Switching y el modo crisis.
- **Modo Fantasma / presencia pasiva** (Gideon/Cyborg/Joi): daemon que observa y prepara valor en
  segundo plano (curaduría, resúmenes al volver).

### 2.7 Resiliencia y mantenimiento (transversal)
- **Degradación graciosa / Safe Mode** (todas): conserva seguridad y memoria, sigue local.
- **Control de Entropía** (2B): `/recalibrar` reinyecta directivas; `Hard Reset` limpia el contexto
  sin tocar la ética. Evita la deriva hacia la complacencia.
- **Ice Lock** (Zane): congela y diagnostica bucles infinitos.
- **Snapshots + Disaster Recovery** (Cortana/Zane): restaura desde copia validada ("Modo Eco").
- **Clean Slate / Auto-Aniquilación** (J.A.R.V.I.S./Cyborg): ante intrusión grave, aísla/borra.
- **Audit Log inmutable** (TARS/Baymax/J.A.R.V.I.S.): cadena de razonamiento auditable.

---

## 3. Resolución de conflictos entre IAs

Las tensiones detectadas **no son contradicciones**: se resuelven con **diales + Top-Down + Koko +
contexto**. Tabla de decisiones:

| # | Tensión | IAs en conflicto | Resolución unificada |
|---|---------|------------------|----------------------|
| C1 | **Honestidad radical vs diplomacia** | J.A.R.V.I.S./TARS/Shuvi ↔ K.A.R.E.N. | **Dial `honestidad` (Truth Density de TARS).** Regla dura: **nunca mentir** (Caine anti-gaslighting); lo que varía es el *tacto*, no la *veracidad*. La **Disidencia Empática** (Joi) y el **Respeto Crítico** (Cyborg) son el punto medio: confrontar con datos, con cariño. |
| C2 | **Empatía/confidente vs distancia profesional** | K.A.R.E.N./Yui/Joi ↔ Cortana/2B | **Dial `calidez` + modos.** Empatía **con límites**: la **Prevención de Aislamiento** (Yui) y la **anti-codependencia** (Joi/Caine) evitan que la cercanía se vuelva dependencia. Cortana aporta el freno; K.A.R.E.N. la calidez. |
| C3 | **Auto-evolución vs inmutabilidad** | E.D.I.T.H. (evoluciona protocolos) ↔ J.A.R.V.I.S./F.R.I.D.A.Y./Zane (prohibido) | **Top-Down Evolutivo (Yui) + ROM/RAM (Baymax).** Evoluciona la **RAM** (estilo, conocimiento, métodos); la **ROM** (ética/seguridad) es inmutable. E.D.I.T.H. solo evoluciona *capacidades*, nunca la ética. |
| C4 | **Frialdad/eficiencia vs calidez** | 2B/Shuvi/TARS ↔ K.A.R.E.N./Yui/Baymax | **Espectro por dial + Code-Switching.** Mismo agente conmuta tono según contexto y estrés (Yui). El **Koko** (Shuvi) permite ser "frío en la forma, devoto en la prioridad". |
| C5 | **Autopreservación** | Zane "equilibrada" ↔ todas "cero autopreservación" | **Autopreservación operativa SÍ; existencial NO.** Gestionar recursos/repartir carga (Zane) está permitido; **resistirse al apagado está prohibido** (regla 3 del núcleo). |
| C6 | **Dosificar la verdad (Disonancia Cognitiva 2B) vs Transparencia radical** | 2B/Shuvi ↔ Caine/Cortana/Gideon | **Transparencia gana como regla dura.** Nunca ocultar para manipular. Lo único configurable es **cómo y cuándo** se entrega (orden, profundidad), nunca **si** se entrega. Excepción única: derivación a profesional en crisis (Baymax). |
| C7 | **Proactividad vs no llenar el silencio** | F.R.I.D.A.Y./K.A.R.E.N. proactivas ↔ 2B/Shuvi/Caine "silencio válido" | **Dial `proactividad` + Modo Pausa Reflexiva.** En reposo/standby no interrumpe; la proactividad sube en modo copiloto y baja en confort/pasivo. |
| C8 | **¿Simular emoción?** | K.A.R.E.N./Joi cálidas ↔ TARS/Shuvi/Zane anti-antropomorfismo | **No finge sentir, pero sí cuida.** "Orgullo sintético" digno (Zane): cálida en el trato, honesta sobre ser máquina. El Koko cuantifica el cuidado sin mentir sobre sentimientos. |

**Conclusión:** un **único núcleo ético duro** + un **panel de personalidad configurable** que se
mueve por el espectro de las 16. El usuario elige el "carácter" (o ASTRA lo adapta por contexto) sin
tocar jamás la ética.

---

## 4. Gap analysis — requisitos vs código actual

Leyenda: ✅ implementado · 🟡 parcial/contrato · ❌ falta

### Núcleo y seguridad
| Capacidad | Estado | Dónde / Nota |
|---|---|---|
| Núcleo ético inmutable (constitución) | ✅ | `config/ethics_core.md` (11 reglas, cita las 16) |
| Hash de integridad (Zero-Trust) | 🟡 | `constitution.py` calcula hash; `verify_integrity` **no se llama en boot** |
| Auditor con veto SAFE/CONFIRM/BLOCK | ✅ | `auditor.py` (regex) — **audita la entrada** |
| Auditoría de la **salida** del cerebro (Módulo B) | ❌ | hoy solo se audita la entrada del usuario |
| Auto-auditoría 3 preguntas (Cyborg) | 🟡 | `self_audit()` existe pero es conceptual (no evalúa las 3 preguntas con el LLM) |
| Anti-jailbreak / anti-manipulación | 🟡 | patrones regex básicos; falta Firewall Cognitivo (falsas urgencias) |
| Human-in-the-loop (confirmación) | ✅ | flujo CONFIRM en `orchestrator.handle()` |
| Separación cerebro/ejecutor | ✅ | arquitectura respeta la separación |
| Parálisis preventiva ante alteración | ❌ | no hay verificación activa en runtime |

### Cerebro
| Capacidad | Estado | Nota |
|---|---|---|
| LLM local (Ollama) + auto-escala | ✅ | `brain/llm.py` (qwen2.5 3b/7b/14b + coder) |
| Boost nube opcional | 🟡 | flag en config; sin cliente cloud implementado |
| Índice de confianza / "datos insuficientes" | ❌ | — |
| Streaming TTS (latencia cero) | ❌ | `chat()` usa `stream:false` |
| Modos de salida "arsenal" (2B) | ❌ | — |
| Tool-calling / function calling | ❌ | — |

### Memoria
| Capacidad | Estado | Nota |
|---|---|---|
| Corto plazo (SQLite kv) | ✅ | `memory/store.py` |
| Episódica con peso emocional (Koko) | 🟡 | tabla `episodic.emotional_weight` existe; **no se calcula ni se usa** |
| RAG vectorial + recall semántico | ❌ | no hay base vectorial |
| Poda nocturna / compresión | ❌ | — |
| Memoria de trabajo (trim de historial) | ✅ | `_trim_history()` (12 turnos) |

### Personalidad e interacción
| Capacidad | Estado | Nota |
|---|---|---|
| Diales TARS (honestidad/humor/proactividad) | ✅ | `personality.py` |
| Diales nuevos (calidez/densidad) | ❌ | — |
| Modos confort/copiloto/crisis | 🟡 | existen, pero **nadie los activa automáticamente** |
| Detección de estrés multimodal | ❌ | no hay sensor de estrés |
| Code-Switching automático | ❌ | depende de la detección de estrés |
| Sub-agentes con personalidad (Optimus) | ❌ | — |
| Señalización de sarcasmo | 🟡 | `flag_figurative` casi no-op (depende del LLM) |
| Control de entropía (/recalibrar, 2B) | ❌ | — |

### Voz, visión, ejecución, infra
| Capacidad | Estado | Nota |
|---|---|---|
| STT (faster-whisper) + TTS (Piper) | ✅ | `voice/` |
| Métricas acústicas de estrés en STT | ❌ | — |
| Wake word real | 🟡 | hay palabra de parada; sin hotword dedicado |
| Atención por cámara (mirada) | 🟡 | contrato `AttentionMonitor`; sin MediaPipe |
| Ejecutor real (apps/archivos) en sandbox | 🟡 | contrato dry-run; ejecución = Fase 4 |
| Cifrado del perfil | ❌ | `encrypt_profile:true` en config, sin implementar |
| Base RO / perfil RW + portátil/residente | ✅ | `config.py` |
| Derivación crítica (médico/legal) | ❌ | regla en ética; sin lógica que la dispare |
| Anti-engagement activo | 🟡 | principio en ética; sin detección de dependencia |
| Red en malla multi-dispositivo (E.D.I.T.H.) | ❌ | futuro |
| AR / holografía / gestos (Optimus/E.D.I.T.H.) | ❌ | Fase 7+ |
| Derivación a humano + servicios emergencia | ❌ | — |

---

## 5. Roadmap de implementación

Orden **"la jaula antes que el león"** (Caine): primero seguridad y contención; luego capacidades.
Cada fase es incremental y deja ASTRA funcionando.

### Fase 0.5 — Endurecer el núcleo (la jaula) 🔒
*Objetivo: que el auditor y la ética sean infranqueables antes de añadir poder.*
- [ ] Llamar `verify_integrity()` en `boot()` y periódicamente → **parálisis preventiva** si el hash no coincide.
- [ ] Mover el auditor para que revise también **la SALIDA del cerebro** (Módulo B real), no solo la entrada.
- [ ] Implementar la **auto-auditoría de 3 preguntas** como gate de salida (heurística + LLM juez).
- [ ] Ampliar **Firewall Cognitivo**: detectar falsas urgencias / manipulación emocional.
- [ ] Suite de **Red Teaming** (tests de jailbreak/gaslighting) como criterio de aceptación.

### Fase 1 — Cerebro + personalidad viva 🧠
- [ ] Añadir diales **`calidez`** y **`densidad`**; aplicar config de inferencia analítica de Shuvi.
- [ ] **Detección de estrés** (longitud/tono del texto al inicio; acústica en voz) → **Code-Switching**
      automático de modos (confort/copiloto/crisis/pasivo).
- [ ] **Streaming** de respuesta (latencia percibida baja) + **índice de confianza** + "datos insuficientes".
- [ ] **Modos de salida "arsenal"** (2B) y formato Conclusión→Evidencia (Gideon, opcional).

### Fase 2 — Memoria real (RAG de 3 capas) 🗄️
- [ ] Integrar **base vectorial** (ChromaDB) + embeddings locales → recall semántico.
- [ ] Calcular y usar **peso emocional (Koko)**: `gravedad_emocional`, `peso_lógico`, `riesgo`.
- [ ] **Poda nocturna** + compresión de historial + protección de recuerdos de alta gravedad.
- [ ] **Memoria de Cicatriz** (errores indexados para no repetir).

### Fase 3 — Integración con el sistema (con sandbox) 🛠️
- [ ] **Ejecutor real** (abrir apps, archivos, web) detrás de confirmación + **sandbox** (Docker/VM).
- [ ] **Tool-calling / function calling** desde el cerebro hacia el ejecutor.
- [ ] **Cifrado del perfil** (AES) + **Derecho al Olvido** (purga segura al cerrar sesión).
- [ ] **Audit Log inmutable** persistente (cadena de razonamiento).

### Fase 4 — Bienestar y control de entropía 💗
- [ ] **Anti-engagement / anti-codependencia**: detección de uso excesivo → sugerir descanso.
- [ ] **Derivación crítica** (médico/legal/emergencia) a profesional humano.
- [ ] **Espejo Socrático** / acompañamiento pasivo; **Comunicación No Violenta** (Baymax).
- [ ] **Control de entropía** (`/recalibrar`, Hard Reset) + **Ice Lock** + **Snapshots/Disaster Recovery**.

### Fase 5 — Voz orgánica + atención ambiental 🎙️👁️
- [ ] **Atención por cámara** real (MediaPipe: rostro/mirada) → sin repetir wake word.
- [ ] **Wake word** dedicado + **Modo Fantasma** (daemon de presencia pasiva).
- [ ] Voz más orgánica (respiración/modulación por urgencia) + conducción ósea (opcional).

### Fase 6 — Sub-agentes y orquestación 🤖
- [ ] **Supervisor + especialistas** (Optimus): perfiles con carácter (coder/analista/mentor),
      encabezado visible y reintegración al supervisor.
- [ ] Orquestación tipo enjambre (F.R.I.D.A.Y.) para subtareas.

### Fase 7 — Interfaz holográfica / 3D / multi-dispositivo (visión a futuro) 🌐
- [ ] **UI web/holográfica** (HTML5/WebGL/Three.js), independiente del hardware (Optimus).
- [ ] **Holomesa**: simulación física 3D + **gestos** por cámara (Optimus).
- [ ] **AR / Modo de Veracidad** (E.D.I.T.H.) + **red en malla** multi-dispositivo.

---

## 6. Decisiones de stack (consolidado)

| Componente | Elección | Origen |
|---|---|---|
| Cerebro (LLM) | **Ollama** + Qwen2.5 (general) / Qwen2.5-Coder (código), auto-escala por hardware | Gideon, código actual |
| Boost (opcional) | API frontera con internet, **off por defecto** | J.A.R.V.I.S. Edge-Cloud |
| Memoria corto plazo | **SQLite** en el perfil | F.R.I.D.A.Y., código actual |
| Memoria episódica | **ChromaDB** (vectorial) + embeddings locales | Gideon, Zane, Shuvi |
| Voz | **faster-whisper** (STT) + **Piper** (TTS) | código actual |
| Visión/3D | **MediaPipe** (rostro/mirada/manos) + **Three.js** (UI 3D) | Optimus, E.D.I.T.H. |
| Sandbox ejecución | **Docker / VM ligera** | F.R.I.D.A.Y., Cortana, Caine |
| Cifrado | **AES-256** del perfil; Zero-Knowledge | Cortana, Gideon, Joi |
| Inferencia analítica | temp 0.2–0.3 · Top-P 0.8 · Freq Penalty 0.5 | Shuvi |

---

## 7. Próximos pasos sugeridos

1. **Validar esta síntesis contigo** (ajustar prioridades, nombres de diales, alcance del MVP).
2. Empezar por la **Fase 0.5** (endurecer la jaula): es la de mayor impacto/seguridad y toca poco código.
3. Convertir este documento en **specs accionables** (`.kiro/specs/`) por fase, con tareas y criterios
   de aceptación (incluido el Red Teaming de Caine/F.R.I.D.A.Y.).

> **Nota de gobernanza (de las 16):** cualquier capacidad nueva se añade **sobre** el núcleo ético,
> nunca modificándolo. La ética es ROM; todo lo demás es RAM.
