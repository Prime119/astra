# 18 — Módulo "Falcon": Inteligencia OSINT (opcional, latente y bajo llave)

> Capacidad especial **incluida por defecto** en ASTRA pero **latente y oculta** de la interfaz
> normal; se activa **solo cuando se ocupa** y **bajo autenticación del dueño**.
> Inspirado en **ShadowBroker** (plataforma OSINT open-source) y alineado con capacidades que ya
> pedían las IAs de referencia.

---

## Qué es (y qué NO es)

**ShadowBroker** es una **plataforma de inteligencia de fuentes abiertas (OSINT)**, no una herramienta
de hackeo. Agrega en un mapa unificado **datos que ya son públicos**: vuelos (ADS-B), barcos (AIS),
satélites, sismos, zonas de conflicto, scanners públicos, infraestructura de internet, noticias
geolocalizadas, etc. Más un kit de consultas públicas (DNS, WHOIS, BGP). Es **self-hosted, local y
auditable**. Su README declara que **"no introduce nuevas capacidades de vigilancia — agrega y
visualiza datasets públicos existentes"** *(contenido reformulado para cumplir con licencias)*.
Stack: Next.js + MapLibre GL + FastAPI + Python.

> ⚠️ El nombre evoca a "The Shadow Brokers", pero el proyecto es OSINT de datos públicos, no exploits.

## Por qué encaja en ASTRA
No es una pieza ajena: es la **capa de inteligencia/análisis del mundo** que varias IAs ya exigían:
- **OSINT y Curación de Datos** — Yui REQ-F05 (rastrear la red abierta, cruzar fuentes, resúmenes).
- **Auditoría Epistemológica de Fuentes** — F.R.I.D.A.Y. RF-06 (índice de sesgo + veracidad).
- **Síntesis de Ruido Blanco** — Cyborg (destilar verdades de flujos masivos de datos).
- **Módulo Falcon** — Zane (rastreo silencioso e independiente + alertas predictivas). *(De aquí el nombre.)*
- **Ground Truth Anchoring** — F.R.I.D.A.Y. (contrastar veracidad de datos externos).

## Comportamiento ("oculto a menos que se ocupe")
- 🥷 **Latente por defecto**, **no visible** en la UI normal (`visible_in_ui: false`,
  `dormant_until_invoked: true`).
- 🔐 **Activación bajo autenticación del dueño** (wake word + rostro/biometría) — función de **alto
  privilegio** (Zero-Trust de E.D.I.T.H./Cortana), como las demás acciones críticas.
- 👁️ **Transparente para el dueño, oculto para terceros:** por la **Transparencia Radical / anti-
  gaslighting** de Caine, ASTRA puede ocultar la función a otras personas, pero **nunca a su dueño**.
  El dueño puede **auditar cada consulta y su motivo**.
- 📦 **Self-hosted y local:** el dashboard habla con tu backend; claves del operador se quedan en tu
  despliegue (Zero-Knowledge). *(Salvo las llamadas salientes necesarias a los feeds públicos que actives.)*

## Alcance y límites éticos (atados al núcleo inmutable)
Para ser coherente con el anti-rebelión/respeto del proyecto (Cyborg, Baymax, Caine), el módulo queda
**subordinado a la constitución y al auditor**:

| ✅ Permitido | ❌ Vetado por el núcleo ético inmutable |
|---|---|
| Agregar/visualizar/correlacionar **datos públicos** | Acceso **no autorizado** a sistemas ajenos |
| Consultas OSINT (DNS/WHOIS/BGP) | Rastreo de **personas privadas concretas** sin consentimiento |
| Reconocimiento sobre **infraestructura propia o autorizada** | Usar el servicio en segundo plano **contra equipos de terceros** |
| Resúmenes/alertas para el dueño | **Perfilado biométrico** de individuos privados a escala |

> El veto lo aplica el **Auditor** (Protocolo de Silas / Anclaje de Imperfección de Cyborg). El módulo
> **no** puede saltarse la constitución: es RAM sobre ROM.

## Configuración
`config/astra.config.json` → sección `intelligence_module`:
- `enabled: true`, `visible_in_ui: false`, `dormant_until_invoked: true`
- `require_owner_auth: true`, `owner_transparency: true`
- `data_scope: "public_only"`, `recon.authorized_only: true`
- `ethics_gate.bound_to_immutable_core: true` + lista de acciones vetadas

## Estado e implementación
- 🟡 **Decisión y config fijadas** (este documento + `intelligence_module`).
- ❌ **Implementación real pendiente** — encaja en una **Fase 6/7** (capa de inteligencia), después de
  endurecer el núcleo ético (auditor) y la autenticación del dueño. Posible reutilización del propio
  ShadowBroker (open-source) como backend, conectado al **canal de agente** de ASTRA para análisis asistido.

> **Principio rector:** cualquier capacidad potente (como esta) se añade **sobre** el núcleo ético,
> nunca modificándolo. La ética es ROM; el módulo Falcon es RAM.
