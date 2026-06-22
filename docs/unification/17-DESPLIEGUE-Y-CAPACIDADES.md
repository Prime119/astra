# 17 — Requisitos de Despliegue y Capacidades (del usuario)

> Requisitos concretos aportados por el usuario sobre **portabilidad en SSD, instalación como
> servicio del sistema, inmutabilidad copy-on-write, automatización dentro de apps, Holomesa 3D
> con gestos, y activación por voz + atención + reconocimiento facial**.
>
> Este documento **refina y prioriza** partes de `00-SINTESIS-ASTRA.md` y de las IAs #03 (E.D.I.T.H.),
> #07 (Gideon) y #08 (Optimus Prime). Donde hay diferencia, **manda este documento**.

---

## R1 · SSD portátil de 1 TB — "ASTRA siempre conmigo"

- ASTRA vive en una **SSD externa de 1 TB** y se transporta siempre ahí.
- En la SSD conviven:
  - `astra-base/` → **programa + modelos + runtime** (Python embebido, Ollama, modelos). **SOLO LECTURA.**
  - `astra-perfil/` → memoria, aprendizajes y config **de la propia SSD**. Escribible.
- **Autocontenido:** la SSD trae **todo lo necesario** para funcionar sin instalar dependencias en el
  ordenador anfitrión (runtime + modelos empaquetados). *(Gideon: air-gapped/local-first.)*

> ✅ **Ya existe** la base de esto: `config.py` resuelve modo `portable` vs `resident` y nunca escribe
> en `astra-base/`. El marcador `PORTABLE` o `ASTRA_PORTABLE=1` activa el modo portátil.

---

## R2 · Instalación "como parte del sistema" (servicio en segundo plano, sin ser una app)

Al usarlo en un ordenador, ASTRA **no debe aparecer como una aplicación normal** (sin icono en la
barra, sin ventana). Debe comportarse como **un servicio del sistema** que:
- Se **autoinicia al encender** el equipo y corre **en segundo plano** siempre. *(= "Modo Fantasma" de Gideon.)*
- Tiene una **huella mínima** en el anfitrión: solo se registra un pequeño **agente/servicio de
  autoarranque** que apunta a la SSD (o a una copia local mínima); el grueso (modelos, lógica) corre
  desde la SSD/runtime empaquetado, **sin instalar paquetes** en el sistema.

### Implementación por sistema operativo
| SO | Mecanismo de autoarranque en segundo plano (oculto) |
|---|---|
| **Windows** | Servicio de Windows o Tarea Programada "al iniciar sesión", ejecución oculta (sin consola/tray) |
| **macOS** | `LaunchDaemon` (a nivel sistema) o `LaunchAgent` (a nivel usuario) |
| **Linux** | servicio **systemd** (`--user` o de sistema) |

> ⚠️ **Aclaración honesta:** "sin instalar nada" y "que arranque solo al encender" son parcialmente
> opuestos: para autoarrancar **hay que registrar** un servicio/tarea (mínimo). La solución: ese
> registro es lo **único** que se añade al anfitrión; todo lo demás vive en la SSD. Sin runtime que
> instalar, sin app visible. Requiere **permisos de administrador** la primera vez (consentimiento del dueño).

> 🔐 **Ética/seguridad:** corre **oculto** solo en **los dispositivos del propio usuario y con su
> consentimiento**. Todo el procesamiento es local (Zero-Knowledge). No es spyware: es el asistente
> personal del dueño en su propio hardware.

---

## R3 · Inmutabilidad Copy-on-Write (no tocar el original) ⭐

Regla central de datos **en la SSD**:
- Cuando ASTRA hace una **copia de seguridad** o **guarda archivos/información**, **NUNCA modifica el
  archivo original**.
- En su lugar crea **una carpeta adicional (overlay/capa superior)** donde sí puede modificar los
  **cambios**. El original permanece intacto.
- Modelo técnico: **Copy-on-Write / OverlayFS lógico** → `base (lower, RO)` + `overlay (upper, RW)`.
  Las lecturas combinan ambas capas; las escrituras van solo al overlay.

### Aislamiento por dispositivo
- Si ASTRA se **instala en otro dispositivo**, **NO debe arrastrar la información de un proyecto que
  ya existe** en la SSD.
- En ese otro dispositivo se crea **únicamente una carpeta adicional propia** (overlay local de ese
  equipo) donde los cambios sí se pueden modificar, **sin tocar el original** de la SSD.
- Es decir: **cada dispositivo tiene su propio overlay**; los originales (en la SSD) son inmutables y
  compartidos como base de solo lectura.

```
SSD:  astra-base/ (RO)  +  proyectos/ORIGINAL (RO, inmutable)
                                   │
            ┌──────────────────────┼───────────────────────┐
            ▼                       ▼                        ▼
   overlay_SSD/ (RW)        overlay_PC-1/ (RW)        overlay_PC-2/ (RW)
   (cambios en la SSD)     (cambios solo en PC-1)    (cambios solo en PC-2)
```

> ✅ Encaja con el principio actual base-RO/perfil-RW. **Falta** implementar el **overlay
> copy-on-write por proyecto** y el **aislamiento de overlay por dispositivo** (hoy el perfil es uno solo).

---

## R4 · Actuar DENTRO de las aplicaciones (automatización)

- ASTRA debe poder **hacer cosas dentro de las aplicaciones** y **modificarlas según lo que se le pida**
  (no solo abrir/cerrar): manipular contenido, ejecutar acciones en la UI de programas, editar archivos
  de proyecto, etc.
- Esto = **Ejecutor real + Tool-Calling + automatización de UI**, siempre detrás de **auditor +
  confirmación + sandbox**. *(F.R.I.D.A.Y. tool-calling, Caine motor dual, Optimus.)*

### Vías técnicas
- **APIs/CLIs** de las apps cuando existan (lo más fiable y seguro).
- **Automatización de UI** cuando no haya API: `pywinauto`/UIAutomation (Windows), AppleScript/Accessibility
  (macOS), `AT-SPI`/`xdotool` (Linux).
- **Edición de archivos de proyecto** respetando R3 (copy-on-write: cambios al overlay, original intacto).

> 🟡 **Hoy:** `executor/system.py` define el contrato (`OPEN_APP`, `READ_FILE`, `WRITE_FILE`,
> `RUN_SCRIPT`, …) en **dry-run**. **Falta** la ejecución real + automatización de UI (Fase 3).

---

## R5 · Holomesa: simulación 3D holográfica con la mano ⭐

Capacidad de **crear simulaciones 3D holográficas** controladas por **cámara + manos**:

### Gestos (una sola mano)
- **Seleccionar** un objeto (cuando hay más de uno).
- **Mover** de posición, **rotar**, **girar** y **manipular** el objeto.
- Con **una sola mano**, también **mover el espacio/escena** alrededor del/los objeto(s) (paneo de cámara).

### Física por defecto: parámetros de la Tierra — **SIN avisos**
- Los parámetros físicos por defecto son **los de la Tierra** (gravedad 9.81 m/s², etc.).
- ⚠️ **OVERRIDE explícito del usuario sobre Optimus REQ-5.2.2:**
  - **NO** mostrar ninguna **alerta** indicando los parámetros.
  - **NO** mostrar mensaje ni apartado que **diga** los parámetros.
  - Simplemente se aplican en silencio.
- Solo se cambian/mencionan los parámetros **si el usuario lo indica explícitamente** (p. ej. "ponlo en
  gravedad cero" / "como en Marte").

> ❌ **No implementado aún.** Es la Fase 7 del roadmap (Holomesa). Stack sugerido: **MediaPipe Hands**
> (gestos) + motor 3D web **Three.js** + física (cannon-es/rapier) con constantes terrestres por defecto.
> *(Matiz vs Optimus: el banner de parámetros queda eliminado por decisión del usuario.)*

---

## R6 · Activación por voz + atención + reconocimiento facial ⭐

Flujo de activación deseado:
1. **"Oye Astra"** (wake word) **activa la cámara** — para **no** tener que activarla manualmente cada
   vez ni mantenerla siempre encendida (privacidad + batería).
2. Con la cámara activa, mientras **detecte que estamos de frente hablándole**, sabe que **la
   conversación es con ella** y **la continúa** sin repetir "Oye Astra".
3. Cuando **apartamos la mirada**, entiende que **lo que decimos NO es con ella** (ignora).
4. **Reconocimiento facial:** identifica **caras** para saber **con quién está hablando** (dueño vs otras
   personas) — todo **local** (Zero-Knowledge).

> 🟡 **Hoy:** `vision/attention.py` ya modela los estados `LISTENING / PASSIVE / STANDBY` con
> `face_present + looking_at_screen + speaking`. **Refinamientos pedidos:**
> - La **cámara NO está siempre encendida**: se **activa con "Oye Astra"** y se apaga tras `standby_seconds`
>   sin atención (hoy `attention_camera:true` implica siempre activa).
> - Añadir **identidad por rostro** (quién habla) al modelo de atención.
>
> ❌ **Falta** la detección real (MediaPipe Face Mesh + gaze + reconocimiento facial + VAD). Fase 5/7.

### Modelo de atención actualizado
```
"Oye Astra"  ─► enciende cámara ─► ¿rostro presente?
                                   ├─ mirando + hablando ─► LISTENING (responde, identifica quién)
                                   ├─ presente, no mirando ─► PASSIVE (no responde)
                                   └─ ausente N s ─► STANDBY ─► apaga cámara ─► requiere "Oye Astra"
```

---

## Impacto en el roadmap (resumen)

| Req | Estado actual | Fase destino |
|---|---|---|
| R1 SSD portátil autocontenida | 🟡 base/perfil + modo portátil listos; falta empaquetar runtime+modelos | Fase 0.5 / empaquetado |
| R2 Servicio en segundo plano + autoarranque oculto | ❌ | Fase 3 (instaladores por SO) |
| R3 Copy-on-Write + overlay por dispositivo | 🟡 principio RO/RW; falta overlay por proyecto y por equipo | Fase 2/3 |
| R4 Automatización dentro de apps | 🟡 contrato dry-run | Fase 3 |
| R5 Holomesa 3D + gestos (física Tierra sin avisos) | ❌ | Fase 7 |
| R6 Wake word activa cámara + atención + rostro | 🟡 contrato de atención; cámara siempre-on hoy | Fase 5/7 |

> **Orden recomendado** (la jaula antes que el león): primero **R1 + R3** (datos seguros e inmutables),
> luego **R2 + R4** (presencia en el sistema + automatización con auditor/sandbox), y por último
> **R6 + R5** (atención por cámara y Holomesa, que dependen de hardware y visión).
