# 📦 Modelos 3D reales (.glb) → hologramas realistas

Coloca aquí archivos **`.glb`** (modelos 3D reales) y el visor los carga **automáticamente** y les
aplica el **efecto holográfico** cian. Es **mucho más realista** que los modelos dibujados a código
(que quedan solo como respaldo si no hay `.glb`).

> Igual que hiciste con los modelos de IA: descargas el archivo y lo dejas en esta carpeta.
> **Los `.glb` NO van a GitHub** (pesan); viajan con el programa/SSD.

## Nombres de archivo que el visor busca
| Tipo | Archivo en esta carpeta |
|---|---|
| Aerogenerador | `aerogenerador.glb` |
| Torre de transmisión | `torre-transmision.glb` |
| Torre de enfriamiento | `torre-enfriamiento.glb` |
| Subestación | `subestacion.glb` |
| Planta solar | `planta-solar.glb` |
| Presa / hidroeléctrica | `presa.glb` |
| Oficinas CFE | `oficinas.glb` |
| Central nuclear | `central-nuclear.glb` |

> Si falta alguno, ese tipo usa el modelo a código (respaldo). Puedes ir agregándolos de a poco.

## Dónde conseguir modelos `.glb` gratis (con licencia libre)
- **Sketchfab** (filtra por *Downloadable* + licencia *CC*): busca "cooling tower", "electrical substation",
  "wind turbine", "transmission tower", "nuclear power plant", "solar farm", "dam". Descarga en formato **glTF/GLB**.
- **Poly Pizza** (https://poly.pizza) — modelos low-poly gratis, formato GLB.
- **Quaternius / Kenney** — packs gratis (más estilizados).

Descarga el `.glb`, **renómbralo** como la tabla de arriba y déjalo aquí.

## ⚠️ Importante para que cargue
Por seguridad del navegador, cargar `.glb` locales **no funciona con doble clic** (file://).
Ábrelo con un mini-servidor:
```
cd holo-models
python -m http.server 8000
```
y entra a `http://localhost:8000`.

> Con doble clic (file://) verás los modelos **a código** (respaldo); con el servidor + `.glb` verás
> los **realistas**.
