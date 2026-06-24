# 19 — MEC: identidad de la Versión B + monitoreo de activos CFE

> Define la **identidad propia de la Versión B** (se llama **MEC**, voz masculina, se activa con
> **"Oye MEC"**) y la integración del sistema de **monitoreo MEC** (`Prime119/ProyectoMEC`).
> **Solo en la Versión B.**

---

## Identidad de las dos versiones

| | Versión A | Versión B |
|---|---|---|
| **Nombre** | **Astra** | **MEC** |
| **Activación** | "Oye Astra" | **"Oye MEC"** |
| **Voz** | Femenina | **Masculina** |
| **Persona** | General | Ingeniero profesional de CFE |
| **Monitoreo MEC** | ❌ | ✅ |

> El nombre permite saber al instante qué versión se está usando: si responde "Astra" es la A; si
> responde **"MEC"** es la B.

Config: `config/editions/full.json` (identity Astra / voz female) y `config/editions/cfe.json`
(identity MEC / wake "oye mec" / voz male).

---

## Qué es ProyectoMEC

`Prime119/ProyectoMEC` = **"MEC Industrial Analytics Pro"**: consola de **monitoreo eléctrico en
tiempo real** (PyQt6 + TensorFlow). Lee telemetría por **serial/COM** o **simulación**
(`panel_de_control.txt` → `emisor_simulado.py`, 11 valores CSV) y muestra:

### Telemetría monitoreada
- Tensión (V), Corriente (A), Frecuencia (Hz), Factor de Potencia
- Temperatura (°C), Vibración (mm/s), THD (%)
- Potencias: Activa (W), Reactiva (VAr), Aparente (VA)
- **Salud (%)** del activo

### Motor de IA
- **Autoencoder** → detección de anomalías por error de reconstrucción.
- **LSTM** → predicción de la salud futura.
- **Isolation Forest** → detección de outliers.
- Estados: APRENDIENDO → NOMINAL → PREVENCIÓN → ANOMALÍA AE/IF → ANOMALÍA CRÍTICA.

### Normas verificadas
- **IEEE 519** (THD), **ISO 10816** (vibración), **PF ≥ 0.92** (penalización CFE), rangos nominales
  de tensión (110-140 V), frecuencia (55-65 Hz) y temperatura.

---

## Integración con MEC (el asistente)

**Disparador:** en el mapa 3D del módulo **Falcon**, al **seleccionar** una subestación, torre,
línea, estructura, motor o central de CFE → se **abre el monitoreo MEC** de ese activo.

```
[Mapa 3D Falcon]  --selección de activo-->  [Monitoreo MEC]
   subestación / torre / línea / estructura / motor / central
        │
        ▼
   Telemetría en tiempo real (V, I, Hz, PF, °C, mm/s, THD, P/Q/S, salud)
        │
        ▼
   Diagnóstico de condición:  🟢 buenas · 🟡 regulares · 🟠 malas · 🔴 pésimas
   (+ errores, advertencias y observaciones según normas)
        │
        ▼
   MEC (ingeniero de CFE) lo explica por voz/chat
```

### Lo que ya está implementado (probado)
`src/astra/cfe/monitoring.py` — **contrato de datos + clasificador de condición** (lógica pura):
- `AssetReading` (las 11 métricas) + `AssetReading.from_payload(csv)` (lee el formato del emisor de ProyectoMEC).
- `diagnosticar(reading)` → `Diagnostico` con condición + errores/advertencias/ok, usando los mismos
  umbrales y normas de ProyectoMEC.
- `explicar(diagnostico, activo=...)` → texto breve estilo ingeniero MEC.

Escala de condición:
- 🔴 **PÉSIMAS** — algún error crítico o salud < 40%.
- 🟠 **MALAS** — salud < 60% o ≥ 3 advertencias.
- 🟡 **REGULARES** — alguna advertencia o salud < 85%.
- 🟢 **BUENAS** — sin observaciones y salud ≥ 85%.

### Pendiente (fases siguientes)
- 🟡 **Puente con la consola real** (`ProyectoMEC`): lectura serial/COM en vivo + UI 3D embebida.
- 🟡 Disparo desde la **selección en el mapa Falcon** (Fase 6/7).
- 🟡 Motor de IA (Autoencoder/LSTM/IsolationForest) corriendo en línea para predicción de fallas.

Config: `config/editions/cfe.json` → `mec_monitoring` + `intelligence_module.asset_selection_opens`.

> **Solo Versión B (MEC).** En Astra (Versión A) la capacidad `mec_monitoring` está desactivada.
