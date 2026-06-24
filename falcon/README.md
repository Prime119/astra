# 🗺️ Falcon — Mapa de infraestructura CFE (MVP)

App web (solo navegador, **sin instalar nada**) que muestra la infraestructura de **CFE en México**
sobre un **mapa real oscuro** (estilo ShadowBroker), con estados, ciudades y fronteras. Al
seleccionar una estructura, abre un **panel flotante** en la esquina con su monitoreo (telemetría +
condición), **sin tapar el mapa**.

> Es la **Opción B** del proyecto, edición **MEC/CFE**. Pieza de la capa de inteligencia **Falcon**.

## ▶️ Cómo abrirlo
- Doble clic en `falcon/index.html` (se abre en tu navegador), o desde CMD: `start falcon\index.html`.
- Si tu navegador bloquea algo: `cd falcon` y `python -m http.server 8000`, luego abre `http://localhost:8000`.

> Necesita internet para cargar el mapa (MapLibre + tiles de CARTO) y la librería. La versión 100%
> offline se empaqueta más adelante.

## 🕹️ Controles
- **Arrastrar** = mover el mapa · **rueda** = zoom · **clic** en un activo → panel de MEC.
- El zoom **más alejado** está limitado a ver **todo México** (como pediste). No puedes salirte de México.
- 🖐️ **Control con la mano** (cámara): siguiente paso.

## ✨ Qué hace ya
- **Mapa real oscuro de México** (MapLibre + CARTO dark) con nombres de estados/ciudades y fronteras.
- **Cientos de activos CFE** (subestaciones, torres/líneas, hidro, eólica, solar, termo, oficinas)
  distribuidos por el país, con **agrupación (clusters)** al alejarse y puntos individuales al acercarse.
- **Color por condición** (🟢 buenas / 🟡 regulares / 🟠 malas / 🔴 pésimas).
- **Clic → panel flotante MEC** con telemetría en vivo (simulada) + diagnóstico (IEEE 519, ISO 10816,
  PF CFE) + comentario de MEC.

## ⚠️ Honestidad
- Los activos y la telemetría son **representativos/de muestra** (cientos generados dentro del
  contorno de México) para el MVP visual. La estructura está lista para **datos reales**.

## ⏳ Pendiente
- 🌎 **Datos reales** de CFE (OpenStreetMap / datos abiertos) en vez de los de muestra.
- 🖐️ **Control gestual** con la mano (MediaPipe + webcam).
- 🔌 Telemetría en vivo real conectada al activo / a ProyectoMEC.
- 📦 Empaquetado offline (incrustar MapLibre y tiles).
