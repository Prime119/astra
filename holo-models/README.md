# 🧊 FALCON Holo-Modelos — Biblioteca 3D holográfica de estructuras CFE

Proyecto **independiente** (futuro repositorio propio) con los **modelos 3D holográficos** de las
estructuras de CFE, en estilo wireframe cian (como las referencias). Se integrará en el mapa
**Falcon**: al hacer clic en un activo, se mostrará su holograma + las gráficas de MEC.

> ⚠️ **Nota de hosting:** se construyó aquí (en una rama de `astra`) para que puedas **verlo ya**.
> Cuando crees un **repositorio nuevo vacío** en GitHub, esta carpeta se migra tal cual a ese repo.

## ▶️ Cómo abrirlo
- Doble clic en `holo-models/index.html` (o `start holo-models\index.html` en CMD).
- Necesita internet para cargar Three.js (CDN). La versión offline se empaqueta después.

## 🕹️ Controles
- **Arrastra** para rotar · **rueda** para zoom · botones de abajo para cambiar de modelo.

## 🧩 Modelos incluidos (estilo holográfico)
- **Aerogenerador** (central eólica) — con aspas que giran.
- **Torre de Transmisión** (pilón + conductores).
- **Torre de Enfriamiento** (termoeléctrica).
- **Subestación** (transformadores + pórtico/busbars).
- **Planta Solar** (arreglo fotovoltaico).
- **Presa / Hidroeléctrica**.
- **Oficinas CFE** (edificio).
- **Central Nuclear** (domo + torre de enfriamiento).
+ terreno de malla plexus, anillos HUD y partículas, como en las imágenes de referencia.

## ⚖️ Honestidad (qué es real)
- Son **modelos estilizados por TIPO**, no réplicas exactas de cada edificio real (eso no es
  automatizable; sería modelado manual de miles). Lucen como las referencias y cubren los tipos de
  CFE. Estructuras icónicas concretas se pueden refinar a mano más adelante.

## ⏳ Pendiente
- 🔌 Integrarlo en el mapa **Falcon** (clic en activo → este holograma + gráficas MEC en vivo).
- 🎨 Más detalle/realismo por tipo y modelos específicos de sitios icónicos (ej. Laguna Verde).
- 📦 Empaquetado offline (incrustar Three.js).
- 🗂️ Migrar a su **repositorio propio** cuando lo crees.
