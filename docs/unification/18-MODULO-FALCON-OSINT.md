# 18 — Módulo "Falcon": Inteligencia GIS de infraestructura CFE (México)

> Capacidad especial **incluida por defecto** en ASTRA pero **latente y oculta** de la interfaz
> normal; se activa **solo cuando se ocupa** y **bajo autenticación del dueño**.
> Inspirado en **ShadowBroker** (plataforma OSINT/GIS open-source), pero **reenfocado**:
> **solo México y solo infraestructura de CFE** (sin aviones, barcos ni datos globales).

---

## Alcance (lo que pidió el usuario)

- 🌎 **Solo México** (no el mundo entero).
- ⚡ **Solo infraestructura de CFE** (Comisión Federal de Electricidad). **Nada** de aviones, barcos
  ni feeds globales.
- 🗺️ **Mapa 3D navegable con la mano**, pero **solo para mover el espacio** (desplazarse entre
  ciudades, subestaciones, etc.). **No** se manipulan objetos individuales (eso es la Holomesa, R5).

### Capas de activos a detectar/visualizar
- Subestaciones eléctricas
- Líneas de transmisión y de distribución
- Torres eléctricas
- Oficinas y centros de atención
- Hidroeléctricas
- Plantas eólicas
- Plantas solares
- Termoeléctricas y otras centrales
- **Red de fibra óptica de CFE** (CFE TEIT, sobre las líneas de transmisión)
- **Hotspots de "Internet para Todos"**
- **Cobertura satelital de CFE Internet** *(ver nota abajo)*

### Nota sobre "satélites de CFE"
**CFE no opera satélites propios.** CFE Internet (CFE Telecomunicaciones e Internet para Todos —
**CFE TEIT**) usa **capacidad satelital arrendada** —por ejemplo el satélite **SES-17**— para ofrecer
puntos de internet gratuito en México, además de su **red de fibra óptica** tendida sobre las líneas
de transmisión. Por tanto, la "capa satelital" del módulo refleja **la cobertura de CFE Internet**
(arrendada), no satélites propiedad de CFE.
*Fuente: nota de prensa de SES (2023) sobre SES-17 y CFE TEIT. Contenido reformulado para cumplir con licencias.*

---

## Por qué encaja en ASTRA
Es la **capa de inteligencia/análisis** que varias IAs ya pedían, ahora **acotada a un dominio**:
- **Módulo Falcon** — Zane (rastreo silencioso + alertas predictivas). *(De aquí el nombre.)*
- **OSINT y Curación de Datos** — Yui REQ-F05.
- **Síntesis de Ruido Blanco** — Cyborg (destilar señal de flujos masivos).
- **Auditoría Epistemológica de Fuentes** — F.R.I.D.A.Y. RF-06.

## Comportamiento ("oculto a menos que se ocupe")
- 🥷 **Latente por defecto**, **no visible** en la UI normal.
- 🔐 **Activación bajo autenticación del dueño** (wake word + rostro/biometría) — alto privilegio (Zero-Trust).
- 👁️ **Transparente para el dueño, oculto para terceros** (anti-gaslighting de Caine). El dueño audita
  cada consulta y su motivo.
- 📦 **Self-hosted y local** (Zero-Knowledge), salvo las llamadas salientes a los datasets públicos que se activen.

## Control del mapa (manos)
```
Mapa 3D de infraestructura CFE (México)
  └─ Gesto de una mano = MOVER EL ESPACIO (paneo / desplazarse entre ciudades y subestaciones)
     (sin rotar/seleccionar/manipular objetos — eso es exclusivo de la Holomesa, R5)
```
Stack de mapa sugerido: **MapLibre GL + deck.gl** (render 3D) + **MediaPipe Hands** (gesto de paneo).

## Fuentes de datos (públicas / OSINT)
- **OpenStreetMap** (`power=substation` / `line` / `tower` / `plant`).
- **datos.gob.mx** (datos abiertos del gobierno).
- **CENACE / SENER** (datos públicos del sistema eléctrico nacional).
- Información pública de **CFE / CFE TEIT**.
- Imágenes satelitales públicas (p. ej. **Sentinel-2**).

> ⚠️ La disponibilidad y el detalle de cada capa dependen de qué publiquen estas fuentes; se valida
> en implementación.

## Alcance y límites éticos (atados al núcleo inmutable)
| ✅ Permitido | ❌ Vetado por el núcleo ético inmutable |
|---|---|
| Visualizar/analizar infraestructura **pública** de CFE (uso legítimo: sector energético, investigación, planeación) | **Acceso no autorizado** a sistemas/SCADA de CFE o de terceros |
| Navegar el mapa 3D, correlacionar capas públicas | **Facilitar sabotaje/daño/interrupción** de infraestructura crítica |
| Resúmenes/alertas para el dueño | Rastreo de **personas privadas** sin consentimiento |
| | Uso del servicio en segundo plano **contra equipos de terceros** |

> El veto lo aplica el **Auditor** (Protocolo de Silas / Anclaje de Imperfección de Cyborg). El módulo
> **no** puede saltarse la constitución: es RAM sobre ROM.

## Configuración
`config/astra.config.json` → `intelligence_module`:
- `geo_scope: "mexico_only"`, `subject_scope: "cfe_only"`, `data_scope: "public_only"`
- `asset_layers: [...]` (subestaciones, líneas, torres, oficinas, hidro, eólica, solar, fibra, hotspots, satélite)
- `map: { render: "3d", hand_control: "pan_only" }`
- `require_owner_auth: true`, `owner_transparency: true`, `visible_in_ui: false`
- `ethics_gate.bound_to_immutable_core: true` + acciones vetadas

## Estado e implementación
- 🟡 **Decisión y config fijadas** (este documento + `intelligence_module`).
- ❌ **Implementación real pendiente** — **Fase 6/7** (capa de inteligencia), tras endurecer el auditor
  y la autenticación del dueño. Posible reutilización del backend de ShadowBroker (open-source),
  recortado a las capas de CFE/México y al control de mapa por paneo.

> **Principio rector:** capacidades potentes como esta se añaden **sobre** el núcleo ético, nunca
> modificándolo. La ética es ROM; el módulo Falcon es RAM.
