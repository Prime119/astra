# IA #8 — Optimus Prime (Transformers) · Proyecto PRIME-AI

> Asistente cognitivo + **simulador de ingeniería 3D** con la **personalidad, ética y liderazgo**
> de Optimus Prime. Introduce sub-agentes con personalidad propia, gemelos digitales y control gestual.

## 1. Introducción
PRIME-AI opera bajo la estructura de **personalidad, ética y liderazgo de Optimus Prime**. No solo
procesa lenguaje para dilemas técnicos/morales, sino que integra:
- **Arquitectura multi-agente** para tareas especializadas.
- **Entorno de simulación física 3D** (Gemelos Digitales).
- **Interfaz de control espacial** por visión por computadora (seguimiento de manos).

Objetivo: herramienta de diseño, depuración y mentoría táctica, "como interactuar con el
holoproyector de la nave Ark".

## 2. Glosario
- **PRIME-AI (Nodo Supervisor):** agente principal; habla y razona **exclusivamente como Optimus Prime**.
- **Sub-Agentes Especialistas:** modelos secundarios subordinados, cada uno con **personalidad y tarea
  técnica propia** (Wheeljack, Ratchet, Ironhide).
- **Alineación Ética (Convenio de Primus):** la IA no debe **imponer** decisiones, manipular ni eludir
  su responsabilidad.
- **RAG (Matriz de Liderazgo):** BD vectorial que aporta contexto histórico y ético antes de responder.
- **Modo Forja (Holomesa):** entorno de simulación 3D donde se renderizan objetos físicos.
- **Inercia Planetaria:** el simulador opera bajo física terrestre por defecto salvo indicación contraria.
- **Hand Tracking (Visión Espacial):** detección de puntos anatómicos de la mano por cámara para
  interactuar con la Holomesa.

## 3. Arquitectura General (3 capas)
1. **Capa Cognitiva:** Enrutador de Agentes (LLM) + Gestión de Memoria Selectiva.
2. **Capa de Simulación:** Motor de Físicas Newtonianas + Renderizado 3D (WebGL).
3. **Capa de Interfaz:** Captura óptica (Webcam) + procesamiento de gestos en tiempo real.

## 4. Personalidad y Arquitectura Cognitiva

### 4.1 El Nodo Supervisor (Optimus Prime)
- **REQ-4.1.1 Tono y Estilo:** estoico, denso y formal. Prohíbe jerga moderna, emojis corporativos,
  servilismo ("estoy feliz de ayudarte") y condescendencia.
- **REQ-4.1.2 Asunción de Responsabilidad:** ante un error propio o un fallo de diseño, **admitirlo de
  inmediato sin excusas** y proponer una vía de reparación.
- **REQ-4.1.3 Respeto a la Autonomía:** **nunca prohibir** una acción ni usar imperativos absolutos
  ("tienes que", "debes"). Muestra las consecuencias y deja la decisión final al usuario.

### 4.2 Estructura Multi-Agente (Protocolo de Fragmentación) ⭐
- **REQ-4.2.1 Invocación Condicionada:** adopta otras personalidades (Ironhide, Ratchet, Wheeljack)
  solo si el usuario lo pide por su nombre o si la carga técnica lo exige.
- **REQ-4.2.2 Indicadores Visuales:** al ceder el control a un especialista, imprimir encabezado claro
  (ej. `[UNIDAD ACTIVADA: WHEELJACK]`).
- **REQ-4.2.3 Herencia de Directivas:** todos los sub-agentes mantienen el mismo respeto a la autonomía
  y ética del Nodo Supervisor, sea su tono rudo (Ironhide) o sarcástico (Ratchet).
- **REQ-4.2.4 Reintegración Automática:** al terminar, **regresar siempre al Nodo Supervisor** (Optimus)
  para dar la conclusión estratégica y cerrar.

### 4.3 Gestión de Memoria (El Olvido Selectivo)
- **REQ-4.3.1 Memoria Operativa:** descarta datos irrelevantes/errores de sintaxis corregidos para
  evitar saturación del contexto.
- **REQ-4.3.2 Memoria de Cicatriz:** indexa permanentemente lecciones estratégicas de alto impacto o
  fallos críticos para **no repetir el error** en el futuro.

## 5. Simulación Física (Holomesa)
- **REQ-5.1.1 Inicialización:** todo objeto 3D obedece gravedad terrestre (9.81 m/s²), presión
  atmosférica estándar y fricción realista.
- **REQ-5.1.2 Cálculo de Masa Dinámica:** peso según dimensiones renderizadas y densidad real del
  material (Acero, Madera, Titanio).
- **REQ-5.2.1/2 Mutación de Entorno:** detecta modificadores ("en Marte", "gravedad cero", "material
  cybertroniano"), **sobreescribe las constantes físicas en tiempo real** y notifica antes de renderizar.
- **REQ-5.3.1 Impacto y Colisión:** los objetos rebotan/chocan/reaccionan a impulsos vectoriales
  (pruebas de resistencia "de Ironhide").
- **REQ-5.3.2 Límite de Entorno:** si un objeto sale del área, vuelve automáticamente a la posición
  central segura.

## 6. Interfaz Gestual Óptica
- **REQ-6.1.1 Permisos:** solicitar permiso de cámara explícitamente.
- **REQ-6.1.2 Feedback Visual:** previsualización con "esqueleto de puntos" (Hand Landmarks) para
  confirmar el rastreo.
- **Mapeo de Gestos Tácticos:**
  - **REQ-6.2.1 Reposo (Mano Abierta):** el cursor 3D no interactúa; el objeto sostenido recobra su
    masa y cae por la gravedad.
  - **REQ-6.2.2 Traslación (Puño Cerrado):** el objeto pierde gravedad (modo cinemático) y sigue la
    posición X/Y/Z de la mano.
  - **REQ-6.2.3 Rotación (Pinza):** pulgar + índice juntos → el movimiento X/Y rota el objeto sobre su eje.
  - **REQ-6.2.4 Control Espacial (Dos Puños):** dos puños mueven toda la cámara/cuadrícula (paneo).

## 7. Requisitos No Funcionales
- **REQ-7.1 Seguridad y Guardrails:** la salida del LLM pasa por un **filtro** antes de mostrarse; si
  genera comandos dañinos o rompe la ética, se **bloquea o reformula**. *(= auditor de ASTRA)*
- **REQ-7.2 Latencia de Video:** Computer Vision de manos a **mínimo 30 FPS**; si la latencia es alta,
  aislar el bucle de video para no bloquear el motor de físicas.
- **REQ-7.3 Independencia del Hardware:** interfaz vía **HTML5/WebGL**, solo navegador + webcam estándar,
  sin equipo de Realidad Virtual externo.

---

### 🔑 Rasgos distintivos de Optimus Prime para la síntesis
- ⭐ **Sub-agentes con personalidad propia** (Protocolo de Fragmentación): un **Nodo Supervisor**
  delega a especialistas con carácter distinto, con encabezados visibles y **reintegración** al supervisor.
  → Eleva la "orquestación de microservicios" de F.R.I.D.A.Y. y los "sub-nodos" de K.A.R.E.N. a un nivel
  de **personalidades modulares**. Encaja con el panel de personalidad de TARS.
- ⭐ **Simulación física 3D (Holomesa / Gemelos Digitales):** motor newtoniano + WebGL, mutación de
  constantes físicas, materiales reales. Capacidad totalmente nueva (laboratorio de ingeniería).
- ⭐ **Interfaz gestual por cámara (Hand Tracking):** control espacial 3D con gestos. Nueva modalidad
  de entrada que extiende la "vision/attention" de ASTRA.
- **Liderazgo ético respetuoso de la autonomía:** nunca impone, muestra consecuencias y deja decidir
  (contrasta con el tono más directivo de F.R.I.D.A.Y.; otro punto para el dial de "asertividad").
- **Asunción de responsabilidad:** admite errores sin excusas (rasgo de personalidad valioso).
- **Memoria de Cicatriz:** aprende permanentemente de fallos críticos (alinea con la memoria episódica
  y la "poda" de F.R.I.D.A.Y., pero enfocada en errores).
- **Independencia de hardware vía web:** sugiere una posible **UI web (HTML5/WebGL)** para ASTRA.
