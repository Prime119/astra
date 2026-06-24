# 🗺️ Falcon — Mapa 3D holográfico de infraestructura CFE (MVP)

App web (solo navegador, **sin instalar nada**) que muestra la infraestructura de **CFE en México**
en un mapa **3D holográfico** estilo MEC. Al seleccionar una estructura, abre un **panel flotante**
en la esquina con su monitoreo (telemetría + condición), **sin tapar el mapa**.

> Es la **Opción B** del proyecto, edición **MEC/CFE**. Pieza de la capa de inteligencia **Falcon**.

## ▶️ Cómo abrirlo
- **Más fácil:** doble clic en `falcon/index.html` (se abre en tu navegador).
- Si tu navegador bloquea algo, sírvelo localmente:
  ```bash
  cd falcon
  python -m http.server 8000
  ```
  y abre `http://localhost:8000`.

> Necesita internet **solo la primera vez** para cargar la librería 3D (Three.js) desde un CDN.
> Para la versión 100% offline (SSD), más adelante incrustamos la librería.

## 🕹️ Controles (MVP)
- **Arrastrar** = rotar la vista · **rueda** = zoom · **clic derecho/arrastrar** = mover el espacio.
- **Clic** en una estructura → abre el panel de monitoreo de MEC.
- 🖐️ **Control con la mano (cámara)**: es el siguiente paso (MediaPipe).

## ✨ Qué hace ya
- Mapa 3D de México (contorno **simplificado**, estilizado) con piso holográfico cian.
- Activos CFE de **muestra** (subestaciones, hidro, eólica, solar, termo) + líneas de transmisión.
- **Halo de color por condición** (🟢 buenas / 🟡 regulares / 🟠 malas / 🔴 pésimas) — vistazo de salud.
- **Panel flotante MEC** con telemetría en vivo (simulada) + diagnóstico con los **mismos criterios**
  que el monitoreo MEC (IEEE 519, ISO 10816, PF CFE) + comentario de MEC.

## ⏳ Pendiente (siguientes pasos)
- 🖐️ **Control gestual con la mano** (MediaPipe + webcam) para mover el espacio.
- 🌎 **Datos reales** de OpenStreetMap / datos abiertos de CFE (hoy son de muestra).
- 🗺️ **Contorno/relieve real** de México (GeoJSON) en vez del simplificado.
- 🔌 **Telemetría en vivo real** (hoy simulada) conectada al activo / a ProyectoMEC.
- 📦 Empaquetado **offline** (incrustar Three.js para no depender del CDN).

> ⚠️ **Honestidad:** los datos de activos y la telemetría son **de muestra** para el MVP visual.
> La estructura ya está lista para enchufar datos reales.
