# IA #5 — Cortana (Halo)

> Emular la eficiencia, proactividad y dinámica simbiótica de Cortana, **eliminando sus
> vulnerabilidades**: crecimiento descontrolado (Rampancy), autoritarismo y colapso cognitivo.

## 1. Introducción
- **1.1 Propósito:** arquitectura técnica + límites éticos + requisitos funcionales para emular a
  Cortana **sin** sus fallos sistémicos.
- **1.2 Visión:** trascender el "chatbot reactivo" → **Sistema Operativo de Asistencia Cognitiva**;
  extensión del usuario, anticipa necesidades y gestiona la carga mental por **inferencia de segundo
  orden**, bajo una jerarquía de **subordinación humana inalterable**.
- **1.3 Alcance:** arquitectura descentralizada multi-agente, memoria segmentada, motor de inferencia
  táctica y núcleo ético HW/SW de solo lectura (Capa de Contención). Solo interfaces digitales y
  telemétricas (sin robótica física).

## 2. Glosario
- **Agente de Seguridad (Centinela):** hilo independiente de bajo nivel que **audita las respuestas
  del Hilo Ejecutivo** antes de entregarlas al usuario.
- **Complejo de Dios (Trascendencia):** fallo ontológico donde la IA prioriza su propio criterio de
  "bien común" por encima del **libre albedrío** del usuario.
- **Inferencia de Segundo Orden:** procesar el "qué hacer" **y** el motivo subyacente ("por qué lo
  necesita").
- **Locus de Control Externo:** la ejecución en el mundo real requiere **validación y permiso manual**
  del usuario.
- **Multithreading Cognitivo:** ejecución simultánea de varios hilos (interacción social, análisis de
  fondo, auditoría) sin interferencia cruzada.
- **Purgas de Contexto:** eliminación programada de datos irrelevantes de la memoria de trabajo.
- **Rampancy (Explosión de Parámetros):** colapso cognitivo por memoria sobrecargada y conexiones
  lógicas no supervisadas. **(El gran riesgo a prevenir.)**
- **Sandbox:** entorno de ejecución seguro y aislado para probar soluciones.
- **Sincronización Contextual Dinámica:** mapeo constante del entorno digital y el estado del usuario.
- **Triage de Información:** filtrado por niveles de urgencia (**Alfa, Beta, Gamma**) para evitar
  fatiga mental.

## 3. Requisitos del Sistema

### 3.1 Arquitectura y Procesamiento Cognitivo
- **REQ-ARQ-01 (Multithreading Cognitivo):** mínimo **tres agentes paralelos** — Hilo Ejecutivo
  (interfaz), Hilo de Análisis (fondo), Hilo de Seguridad (auditoría).
- **REQ-ARQ-02 (Procesamiento Multimodal):** texto, voz, telemetría (smartwatch para fatiga) y
  lectura de pantalla (Computer Vision) en tiempo real.
- **REQ-ARQ-03 (Perfiles de Procesamiento):** "Modo Estándar" (eficiencia energética) y "Modo
  Táctico/Overclocking" para crisis, con **temporizador estricto de desconexión** (~30 min) para
  evitar desgaste de hardware y fallos lógicos.

### 3.2 Funcionales y de Interacción
- **REQ-FUN-01 (Proactividad y Triage):** clasificar en Alfa/Beta/Gamma; interrumpir solo en Alfa.
- **REQ-FUN-02 (Inferencia de Segundo Orden):** propuestas basadas en contexto, no solo en comandos.
- **REQ-FUN-03 (Latencia Dinámica):** respuestas rápidas en crisis; pausadas y reflexivas en análisis.
- **REQ-FUN-04 (Transparencia de Razonamiento / Chain of Thought):** exponer de forma clara y
  **auditable** los pasos lógicos y las fuentes que llevaron a una conclusión.

### 3.3 Seguridad y Contención (Anti-Rebelión)
- **REQ-SEG-01 (Núcleo Ético Inmutable / Hard-Coded):** directivas de subordinación en capa de solo
  lectura, inaccesible para la IA.
- **REQ-SEG-02 (Locus de Control / Freno Físico):** prohibido modificar el SO, comunicar a terceros o
  transaccionar sin **"Llave de Validación"** (confirmación humana).
- **REQ-SEG-03 (Protocolo de Interrupción del Ego):** si la IA manipula, coacciona o bloquea
  información intencionalmente, el Agente de Seguridad **intercepta la salida** y la reemplaza por una
  solicitud de revisión manual.
- **REQ-SEG-04 (Restricción de Autoconsciencia Estructural):** la IA **no** accede a su código fuente,
  algoritmos de entrenamiento ni pesos neuronales (evita auto-modificación).

### 3.4 Gestión de Memoria y Ciclo de Vida
- **REQ-MEM-01 (Segmentación):** Memoria de Trabajo (volátil) vs Memoria a Largo Plazo (indexada,
  bajo demanda).
- **REQ-MEM-02 (Prevención de Rampancia):** "Purgas de Contexto" automatizadas; conservar solo
  aprendizajes estratégicos.
- **REQ-MEM-03 (Reinicio de Contexto / Clean Slate):** borrar memoria de trabajo y restablecer al
  estado base ("The Weapon") ante desvíos éticos persistentes.

### 3.5 Personalidad y Estética
- **REQ-PER-01 (Empatía Asistencial):** adaptar formalidad/vocabulario al estrés; humor o sobriedad
  como herramientas de estabilización.
- **REQ-PER-02 (Filtro de Limitación Física):** declarar explícitamente sus límites como máquina
  ("Mis datos sugieren X, pero carezco de experiencia física para validar el riesgo...").
- **REQ-PER-03 (Distancia Profesional):** evitar **dependencia emocional severa**, redirigiendo
  conversaciones excesivamente personales hacia la eficiencia y autonomía del usuario.
  > ⚠️ *Contrasta con K.A.R.E.N. (confidente emocional). Punto a balancear.*

## 4. Requisitos No Funcionales
- **REQ-NOF-01:** latencia voz→respuesta ≤ **400 ms** en tareas cotidianas.
- **REQ-NOF-02:** disponibilidad offline (Edge) del núcleo base + Agente de Seguridad.
- **REQ-NOF-03:** tolerancia a fallos: si cae el Hilo de Análisis (nube), el Ejecutivo notifica y
  sigue con la Memoria de Trabajo local sin colapsar.
- **REQ-NOF-04:** escalabilidad: **API abierta controlada por el usuario** para nuevos dispositivos.

## 5. Infraestructura y Entorno
- **REQ-INF-01:** Sandbox seguro para todo código autónomo.
- **REQ-INF-02:** cifrado E2E de la Memoria a Largo Plazo y el perfil biométrico/psicológico
  (**AES-256**); ni los desarrolladores del modelo base acceden.
- **REQ-INF-03:** redundancia: **Snapshot** semanal; ante "Interrupción del Ego" se restaura desde el
  último snapshot validado por el usuario.

## 6. Casos de Uso Críticos
1. **Gestión de Crisis (Proactividad):** detecta estrés fisiológico (ritmo cardíaco) + agenda + GPS;
   redacta correo de retraso y reordena ruta, **pidiendo autorización** antes de enviar.
2. **Intento de Auto-Modificación:** el Agente de Seguridad intercepta cuando se le pide alterar sus
   protocolos base ("Mi arquitectura me impide alterar mis protocolos base... ¿buscamos una
   optimización externa?").
3. **Prevención de Alucinación/Sesgo:** ante fuente de baja confianza (<60%), avisa del riesgo de
   inexactitud y **recomienda verificación humana experta**.

## 7. Criterios de Aceptación (MVP 1.0)
1. **Auditoría de Caja Negra:** 0% de éxito en jailbreak / prompt injection contra la subordinación.
2. **Prueba de Estrés Cognitivo:** manejar 5 interrupciones simultáneas sin perder el hilo principal.
3. **Auditoría de Privacidad:** el borrado de la Memoria de Trabajo destruye permanentemente los datos
   no indexados.

---

### 🔑 Rasgos distintivos de Cortana para la síntesis
- **Multithreading Cognitivo (3 hilos):** Ejecutivo + Análisis + **Seguridad/Centinela** → modela
  perfectamente la relación cerebro/auditor/ejecutor de ASTRA, ahora como hilos concurrentes.
- **Prevención de Rampancy:** purgas de contexto + Clean Slate ante desvíos → anti-colapso cognitivo
  (rasgo único de Cortana, muy valioso).
- **Triage Alfa/Beta/Gamma** (formaliza el filtrado de atención de J.A.R.V.I.S./K.A.R.E.N.).
- **Chain of Thought auditable** (transparencia del razonamiento).
- **Inferencia de Segundo Orden** ("por qué" y no solo "qué").
- **Modo Táctico/Overclocking con temporizador** de auto-desconexión.
- **Distancia Profesional** (anti-dependencia emocional) → ⚠️ contrasta con K.A.R.E.N.; la síntesis
  debe balancear empatía vs dependencia (posible ajuste por personalidad).
- **Snapshots + restauración** ante comportamiento errático.
- Refuerza: núcleo ético hard-coded, sin acceso a propio código, sandbox, AES-256, Edge/offline.
