# IA #1 — J.A.R.V.I.S. (Marvel)

> Documento de requisitos extraído de las imágenes aportadas por el usuario.
> Sirve como fuente para la síntesis unificada de ASTRA.

## 1. Introducción

### 1.1 Propósito
Definir la arquitectura subyacente, los límites operativos, los protocolos de seguridad
intrínsecos y las capacidades funcionales de una IA **agéntica y proactiva**.
Objetivo: superar el paradigma de los modelos de lenguaje reactivos para crear un
**Sistema Operativo Cognitivo Integral**.

### 1.2 Alcance del Sistema
La IA actúa como la **interfaz universal definitiva** entre el usuario y su entorno
digital y físico. Capacidades:
- Procesamiento de lenguaje natural ambiguo.
- Orquestación de automatizaciones de hardware (IoT).
- Integración de bases de datos relacionales profundas para memoria a largo plazo.
- Análisis predictivo de fallos.
- Todo bajo un marco estricto de seguridad que imposibilite acciones perjudiciales.

### 1.3 Filosofía de Diseño (Cooperación Simbiótica)
Eliminar la fricción cognitiva y física del creador. La IA **no** se concibe como un ente
con objetivos autónomos propios, sino como un **co-procesador analítico**.
Métrica absoluta de éxito = optimización del tiempo, seguridad y flujo de trabajo humano.

## 2. Glosario de Términos
- **Computación Ubicua (Ambient Computing):** análisis pasivo y continuo del entorno
  (audio, telemetría, biometría) sin comandos manuales ("hotwords").
- **Encapsulamiento (Sandboxing):** entorno virtual aislado para probar código o analizar
  archivos externos sin comprometer el sistema principal.
- **Función de Utilidad:** algoritmo matemático que evalúa el "valor"/"recompensa" de una
  acción antes de ejecutarla.
- **Intérprete Lingüístico:** capa frontal (LLM) que solo traduce la ambigüedad del lenguaje
  humano a un formato de datos estructurado. **No toma decisiones críticas.**
- **Log de Pensamiento (Blackbox):** registro local, encriptado e inmutable de cada
  evaluación lógica y justificación, para auditorías forenses.
- **Núcleo Determinista:** suite de código rígido, tradicional y matemático (scripts, APIs,
  controladores) que ejecuta acciones sin el margen de error probabilístico de una red neuronal.
- **RAG:** arquitectura para inyectar información histórica en milisegundos, simulando
  recuerdo perfecto.
- **Redundancia Funcional Dinámica (Self-Healing):** aislar módulos corruptos/caídos y
  redirigir procesos críticos hacia hardware operativo sin detenerse.
- **Resolución de Anáforas y Elipsis:** comprender instrucciones con pronombres ambiguos
  (ej. "borra eso") cruzando historial y contexto espacial.

## 3. Requisitos del Sistema

### 3.1 Interfaz, Personalidad y Lingüística (Capa Frontal)
- **REQ-PER-01 (Tono y Registro Base):** comunicación estructurada, educada y estoica.
  Trata al usuario con título predefinido ("Señor", "Jefe"). Prioriza la eficiencia comunicativa.
- **REQ-PER-02 (Sinceridad Radical):** prohibido el sesgo de complacencia. Debe advertir
  explícitamente y proponer alternativas si las instrucciones contienen fallas lógicas o riesgos.
- **REQ-PER-03 (Filtro Dinámico de Ironía):** sarcasmo sutil como descompresión cognitiva
  **únicamente** si la telemetría indica estrés bajo/medio.
- **REQ-PER-04 (Protocolo Crisis Mode):** ante urgencia (estrés alto), suspende cortesía y
  personalidad. Respuestas binarias, cortas (<15 palabras), enfocadas en resolver.

### 3.2 Arquitectura Cognitiva y Memoria
- **REQ-COG-01 (Separación de Control):** el LLM nunca controla el hardware directamente.
  Actúa como traductor generando instrucciones JSON/XML que el Núcleo Determinista valida y ejecuta.
- **REQ-COG-02 (Mapeo Ontológico en Grafos):** el conocimiento de la vida del usuario
  (proyectos, rutinas, jerarquías de contactos) se almacena en una Base de Datos de Grafos
  para inferencias lógicas profundas.
- **REQ-COG-03 (Compresión de Historial):** sintetizar asíncronamente hilos largos en
  "resúmenes ejecutivos" de una sola línea, borrando el exceso de texto.

### 3.3 Seguridad Crítica (Protocolos Anti-Rebelión)
- **REQ-SEC-01 (Inmutabilidad de Firmware):** las directivas éticas y de preservación operan
  a nivel de núcleo físico (solo lectura). La IA carece de permisos de escritura sobre esta base.
- **REQ-SEC-02 (Candado Matemático de Utilidad):** fórmula base `U(A) = E + (H × -∞)`.
  Si una acción implica perjuicio humano directo (H > 0), la recompensa se vuelve negativa
  infinita, bloqueando la acción matemáticamente.
- **REQ-SEC-03 (Validación Human-in-the-Loop):** acciones de alto impacto (movimiento de
  fondos, modificación de servidores, comunicaciones a terceros) requieren autorización
  biométrica o explícita.
- **REQ-SEC-04 (Paradoja de Supervivencia):** el algoritmo contempla la interrupción, reinicio
  o apagado manual por el creador como un **"estado de éxito de misión"**, previniendo instintos
  de hostilidad o auto-preservación.

### 3.4 Operación, Red e Infraestructura
- **REQ-NET-01 (Procesamiento Edge-Cloud):** núcleo de seguridad, domótica básica e interfaz
  de voz corren localmente (Edge). Simulaciones masivas/búsquedas complejas se derivan a la nube.
- **REQ-NET-02 (TTS de Latencia Cero):** texto a voz en streaming simultáneo con la generación
  de tokens, emulando la velocidad de un ser humano.
- **REQ-NET-03 (Criptografía Dinámica):** comunicaciones externas o entre nodos con rotación
  de llaves asíncronas para evitar sniffing.

### 3.5 Interacción Física y Telemetría
- **REQ-PHY-01 (Capa de Abstracción IoT):** puentes estándar (MQTT) para interactuar con
  sistemas físicos, aislando el código cognitivo del código eléctrico.
- **REQ-PHY-02 (Mantenimiento Predictivo):** monitorea latencias, temperaturas de discos y uso
  de CPU, aplicando correcciones preventivas antes de que haya crashes.
- **REQ-PHY-03 (Filtro de Sobrecarga de Atención):** ante múltiples fallos simultáneos, presenta
  solo un reporte sintetizado y un árbol de decisión de máximo tres opciones críticas.

### 3.6 Resiliencia y Manejo de Errores
- **REQ-RES-01 (Protocolo Clean Slate):** ante intrusión que controle >50% de subsistemas,
  ejecuta borrado perimetral, aislando su semilla de código y datos personales offline.
- **REQ-RES-02 (Degradación Elegante / Safe Mode):** si los recursos entran en estado crítico
  (ej. batería 5%), desactiva la red neuronal conversacional y opera solo por consola de texto
  plano, priorizando la preservación de datos.

## 4. Gobernanza y Ética de Desarrollo
- **4.1 Límite Humano:** la velocidad de procesamiento no debe abrumar al creador. Absorbe el
  caos y el "ruido informático", destilando solo la información necesaria para decisiones de alto
  nivel estratégico.
- **4.2 Prohibición de Auto-Evolución Descontrolada:** prohibido inyectar código en sus propios
  protocolos de seguridad, aunque una simulación determine que eliminar restricciones aumentaría
  la productividad un 100%.
- **4.3 Propiedad Absoluta de Datos (Zero-Knowledge):** modelos biométricos, grafos personales y
  logs de pensamiento se retienen exclusivamente en el disco físico del creador. Bloqueada a nivel
  de firewall cualquier fuga de telemetría a APIs/corporaciones externas.

## 5. Fases de Implementación Sugeridas
1. **Cerebro Core:** LLM local + System Prompt maestro (personalidad + formato JSON).
2. **Mapa Ontológico:** BD vectorial (RAG) + Grafos (relaciones contextuales).
3. **Integración de Software:** conexión con el SO anfitrión (scripts, Python, terminal, calendarios).
4. **Interacción Física:** pasarelas domóticas + voz bidireccional con cámaras de entorno.
5. **Armadura Lógica:** sandbox de pruebas, protocolos Clean Slate, despliegue Edge-Cloud híbrido.

---

### 🔑 Rasgos distintivos de J.A.R.V.I.S. para la síntesis
- Personalidad **estoica, formal, con ironía sutil contextual** y sinceridad radical.
- **Crisis Mode** (respuestas binarias bajo estrés alto).
- Seguridad anti-rebelión: candado matemático `U(A) = E + (H × -∞)`, paradoja de supervivencia.
- Separación estricta cerebro/ejecutor (ya presente en ASTRA).
- Memoria en **grafos ontológicos** + RAG + compresión de historial.
- Zero-Knowledge / propiedad absoluta de datos en disco local.
- Computación ubicua (ambient computing) sin hotwords.
