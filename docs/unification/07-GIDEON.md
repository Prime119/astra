# IA #7 — Gideon (The Flash)

> ⚠️ La imagen llegó etiquetada como "Optimus Prime", pero el documento describe **Gideon**.
> Registrado como Gideon. (Si era intencional usar el arquetipo de Optimus, avisar para renombrar.)

> **SRS** del "Proyecto Gideon": agente de IA **local, autónomo, con memoria persistente**,
> arquetipo de **Inteligencia Ambiental**. Es el documento más concreto a nivel de **stack técnico**.

## 1. Introducción
Agente de IA **local (Local-First)**, autónomo, con memoria persistente. Frente a asistentes
comerciales (nube/reactivos), Gideon es un **"Sistema de Observación y Análisis Clínico"**
totalmente privado, enfocado en la **integridad de la información** del usuario.
Prioriza: **economía del lenguaje, precisión objetiva y ausencia de sesgos conversacionales**.
Actúa como **bóveda de memoria inmutable** y **orquestador de tareas** que evoluciona desde la
consulta de texto hacia la integración ambiental proactiva.

## 2. Glosario
- **LLM Local:** LLM ejecutado íntegramente en el hardware del usuario sin APIs externas →
  privacidad y autonomía absolutas.
- **RAG:** combina generación del LLM con recuperación desde BD vectorial privada → "memoria"
  contextual a largo plazo.
- **Base de Datos Vectorial:** almacenamiento especializado (**ChromaDB, FAISS**) de vectores
  multidimensionales para búsquedas semánticas.
- **Orquestador / Agente:** capa lógica intermedia (**LangChain, CrewAI**) que permite al LLM decidir
  cuándo usar herramientas, consultar memoria o interactuar con el SO de forma autónoma.
- **Zero-shot Persona:** definir personalidad (clínica, objetiva) y restricciones desde el inicio de
  la inferencia vía Prompt Engineering.
- **Inteligencia Ambiental (Ambient AI):** procesar datos de forma **pasiva** (segundo plano) según
  eventos y sensores del entorno, minimizando comandos explícitos.
- **Línea de Base (Baseline):** estado original, no corrupto y validado de la información del usuario,
  contra el cual se evalúa cualquier **anomalía** temporal o de datos.

## 3. Requisitos del Sistema

### 3.1 Arquitectónicos (Hardware y Software) ⭐ *stack concreto*
- **Motor de Inferencia Local:** **Ollama** o **LM Studio** para hospedar modelos **cuantizados**
  (ej. **Llama 3 8B** o **Mistral**) minimizando el consumo de VRAM.
- **Almacenamiento de Memoria Vectorial:** BD vectorial **persistente en disco local** para el RAG →
  la **"Bóveda del Tiempo"** del usuario.
- **Capa de Orquestación y Enrutamiento:** framework de agentes (ej. **LangChain**) para enrutar el
  flujo entre la BD, el LLM y la terminal de comandos.

### 3.2 Funcionales
1. **Ingesta de Datos Continua:** vectorizar e indexar documentos locales (PDFs, TXT, bases de
   conocimiento) y logs para actualizar su línea de base.
2. **Protocolo de Economía de Lenguaje:** el prompt maestro fuerza salidas sin lenguaje coloquial.
   Formato obligatorio: **Conclusión → Evidencia → Solicitud de Confirmación (opcional)**.
3. **Cálculo de Probabilidad y Confianza:** toda respuesta predictiva incluye un **índice de confianza
   porcentual** (ej. `[Índice de Confianza: 92.4%]`) para limitar la alucinación.
4. **Gestión de Conflictos de Estado y Versionado:** si una instrucción contradice el archivo
   histórico, interrumpir y emitir **"Anomalía en la Línea de Base"** (gestión de paradojas).
5. **Modo Fantasma (Observador):** ejecutarse como **daemon** en segundo plano analizando los logs
   de actividad del SO pasivamente.

### 3.3 No Funcionales
- **Privacidad Aislada (Air-Gapped):** 100% funcional **sin conexión a internet**. Sin telemetría ni
  reportes a servidores externos (AWS, Google, OpenAI).
- **Tolerancia a Fallos e Integridad:** la BD vectorial **no** sobrescribe bloques de memoria críticos
  sin confirmación explícita → inmutabilidad del historial.
- **Latencia Optimizada:** recuperaciones de memoria (BD vectorial) en **< 1000 ms**.
- **Desacoplamiento Tecnológico:** el orquestador está separado del LLM fundacional → **actualizar el
  "cerebro" sin perder los "recuerdos"** (memoria de ChromaDB).

## 4. Secuencia Lógica de Inicialización (código de referencia)
```python
class GideonSystemCore:
    def __init__(self, mode="CLINICAL_OBSERVER"):
        self.mode = mode
        self.llm_engine = LocalLLM(model="llama-3-local")
        self.vector_vault = VectorDB(path="/secure/gideon_vault")
        self.watchdog = AnomalyDetector()

    def boot_sequence(self):
        system_status = self.watchdog.check_baseline(self.vector_vault)
        if system_status == "OK":
            return "[GIDEON_ONLINE] - Escuchando directivas."
        else:
            return "[ALERTA] - Corrupción en la línea de base detectada."
```

---

### 🔑 Rasgos distintivos de Gideon para la síntesis
- ⭐ **Define el stack técnico real** que ASTRA puede adoptar: **Ollama/LM Studio + Llama 3 8B/Mistral**
  (cuantizado) + **ChromaDB/FAISS** (RAG) + **LangChain/CrewAI** (orquestación). ASTRA ya usa Ollama.
- **Desacoplamiento cerebro ↔ memoria:** poder cambiar el LLM sin perder los "recuerdos" → principio
  arquitectónico clave para la longevidad del proyecto.
- **Índice de confianza porcentual** en cada respuesta (formaliza el umbral 95% de TARS y el anti-
  alucinación de Cortana).
- **Formato de salida estructurado:** Conclusión → Evidencia → Confirmación (economía del lenguaje,
  alinea con TARS y J.A.R.V.I.S.).
- **Baseline + detección de anomalías/paradojas:** integridad del historial; alerta si algo
  contradice el estado validado.
- **Modo Fantasma / daemon observador:** computación ambiental pasiva (alinea con el Ambient Computing
  de J.A.R.V.I.S. y los sub-nodos de K.A.R.E.N.).
- **Air-Gapped total:** privacidad absoluta sin internet (versión extrema del Zero-Knowledge de
  J.A.R.V.I.S. y el AES-256 de Cortana).
