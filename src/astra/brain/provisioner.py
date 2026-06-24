"""
Aprovisionador de modelos INCLUIDOS (bundled) — IA portátil autocontenida.

Los modelos viajan DENTRO del programa (carpeta `astra-base/models/`, en la SSD; NO en git por
su tamaño). ASTRA detecta el dispositivo y **activa SOLO el mejor modelo que ese equipo soporte**,
**sin descargar nada de internet**: registra el `.gguf` local en Ollama con `ollama create`.

La detección del archivo es flexible: acepta el nombre exacto configurado o cualquier `.gguf`
que coincida con un patrón (insensible a mayúsculas), para que NO tengas que renombrar lo que
descargas (p. ej. `Qwen2.5-7B-Instruct-Q4_K_M.gguf`).

Si no hay modelos incluidos disponibles, el cerebro cae a los modelos ya descargados en Ollama.
"""
from __future__ import annotations

import fnmatch
import subprocess
import tempfile
from pathlib import Path

from .llm import TIER_ORDER


def _find_gguf(models_dir: Path, entry: dict) -> Path | None:
    """Encuentra el .gguf de un tier: por nombre exacto o por patrón (sin distinguir mayúsculas)."""
    if not isinstance(entry, dict) or not models_dir.is_dir():
        return None
    exact = models_dir / entry.get("gguf", "")
    if entry.get("gguf") and exact.is_file():
        return exact
    pattern = (entry.get("match") or entry.get("gguf") or "").lower()
    if not pattern:
        return None
    for path in sorted(models_dir.glob("*.gguf")):
        if fnmatch.fnmatch(path.name.lower(), pattern):
            return path
    return None


def _best_bundled_for_tier(
    tier: str, bundled: dict, models_dir: Path
) -> tuple[str | None, dict | None, Path | None]:
    """Mejor modelo incluido que el equipo soporta (≤ tier) y cuyo .gguf existe en disco."""
    idx = TIER_ORDER.index(tier) if tier in TIER_ORDER else 0
    for t in reversed(TIER_ORDER[: idx + 1]):  # del tope permitido hacia el más ligero
        entry = bundled.get(t)
        gguf = _find_gguf(models_dir, entry) if isinstance(entry, dict) else None
        if gguf is not None:
            return t, entry, gguf
    return None, None, None


def ensure_bundled_model(
    *,
    tier: str,
    bundled: dict,
    models_dir: Path,
    reachable: bool,
    available: list[str],
) -> tuple[str | None, str]:
    """
    Asegura que el mejor modelo incluido para este equipo esté activo en Ollama.
    Devuelve (nombre_modelo | None, mensaje).
    """
    _t, entry, gguf = _best_bundled_for_tier(tier, bundled, models_dir)
    if not entry or gguf is None:
        return None, "sin modelos incluidos disponibles para este equipo"

    name = entry["name"]
    if name in available:
        return name, f"modelo incluido ya activo ({name})"
    if not reachable:
        return None, "Ollama no está corriendo; no se pudo activar el modelo incluido"

    try:
        with tempfile.TemporaryDirectory() as td:
            modelfile = Path(td) / "Modelfile"
            modelfile.write_text(f"FROM {gguf.resolve()}\n", encoding="utf-8")
            subprocess.run(
                ["ollama", "create", name, "-f", str(modelfile)],
                check=True, capture_output=True, text=True, timeout=900,
            )
        return name, f"modelo incluido activado sin internet ({name})"
    except FileNotFoundError:
        return None, "no encuentro el comando 'ollama' (¿está instalado y en el PATH?)"
    except Exception as exc:  # subprocess error / timeout
        return None, f"no se pudo activar el modelo incluido: {exc}"


def bundled_status(tier: str, bundled: dict, models_dir: Path) -> dict:
    """Resumen para el diagnóstico (--check): qué modelos incluidos están presentes en disco."""
    present = {}
    for t in TIER_ORDER:
        entry = bundled.get(t)
        present[t] = _find_gguf(models_dir, entry) is not None if isinstance(entry, dict) else False
    chosen_t, chosen, _gguf = _best_bundled_for_tier(tier, bundled, models_dir)
    return {
        "dir": str(models_dir),
        "present": present,
        "chosen_tier": chosen_t,
        "chosen_name": chosen["name"] if chosen else None,
    }
