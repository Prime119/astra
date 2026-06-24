# 📦 Modelos incluidos (bundled) — IA portátil autocontenida

Aquí van los **archivos de modelo `.gguf`** que viajan **dentro del programa** (en la SSD).
ASTRA detecta el hardware del dispositivo y **activa solo el mejor modelo que ese equipo
soporte**, **sin descargar nada de internet** (lo registra en Ollama con `ollama create`).

> ⚠️ **Por qué NO están en GitHub:** estos archivos pesan varios GB (en total ~13 GB) y los
> repositorios de Git no admiten archivos tan grandes. Por eso el **código** vive en GitHub,
> pero los **`.gguf`** se colocan aquí (en tu copia / SSD) una sola vez.

## Archivos esperados (nombres según `config/astra.config.json` → `brain.bundled_models`)

| Nivel del equipo | Archivo `.gguf` esperado en esta carpeta | Se activa como |
|---|---|---|
| ligera (≈8 GB RAM) | `qwen2.5-3b-instruct-q4_k_m.gguf` | `astra-qwen2.5:3b` |
| recomendada (≥15 GB) | `qwen2.5-7b-instruct-q4_k_m.gguf` | `astra-qwen2.5:7b` |
| potente (≥30 GB / GPU) | `qwen2.5-14b-instruct-q4_k_m.gguf` | `astra-qwen2.5:14b` |

## Cómo obtener los `.gguf` (una sola vez)

Opción rápida con Ollama (si ya lo tienes): los modelos que descargas con `ollama pull`
quedan en su caché; pero para **incluirlos en el programa** conviene tener el `.gguf` suelto.
Puedes descargarlos, por ejemplo, desde repositorios GGUF de Qwen2.5-Instruct (cuantización
`Q4_K_M` recomendada para equilibrio tamaño/calidad) y **renombrarlos** como la tabla de arriba.

> Coloca solo los que necesites. En una laptop de 8 GB, con el **3B** basta. Los otros sirven
> para cuando instales ASTRA/MEC en equipos más potentes (ahí los elegirá solo).

## Cómo verificar
```
python -m astra --check
```
Te dirá qué modelos incluidos detecta en esta carpeta y cuál activará para tu equipo.

> Si esta carpeta está vacía, ASTRA usa los modelos que tengas descargados en Ollama
> (`ollama pull ...`) como alternativa.
