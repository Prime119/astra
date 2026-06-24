"""
Aprovisionador de modelos INCLUIDOS (bundled) — IA portátil autocontenida.

Los modelos viajan DENTRO del programa (carpeta `astra-base/models/`, en la SSD; NO en git por
su tamaño). ASTRA detecta el dispositivo y **activa SOLO el mejor modelo que ese equipo soporte**,
**sin descargar nada de internet**: registra el `.gguf` local en Ollama con `ollama create`.

Si no hay modelos incluidos disponibles, el cerebro cae a los modelos ya descargados en Ollama
(comportamiento previo).
"""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from .llm import TIER_ORDER


def _best_bundled_for_tier(tier: str, bundled: dict, models_dir: Path) -> tuple[str | None, dict | None]:
    """Mejor modelo incluido que el equipo soporta (≤ tier) y cuyo .gguf existe en disco."""
    idx = TIER_ORDER.index(tier) if tier in TIER_ORDER else 0
    for t in reversed(TIER_ORDER[: idx + 1]):  # del tope permitido hacia el más ligero
        entry = bundled.get(t)
        if isinstance(entry, dict) and entry.get("gguf"):
            if (models_dir / entry["gguf"]).is_file():
                return t, entry
    return None, None


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
    _t, entry = _best_bundled_for_tier(tier, bundled, models_dir)
    if not entry:
        return None, "sin modelos incluidos disponibles para este equipo"

    name = entry["name"]
    if name in available:
        return name, f"modelo incluido ya activo ({name})"
    if not reachable:
        return None, "Ollama no está corriendo; no se pudo activar el modelo incluido"

    gguf = (models_dir / entry["gguf"]).resolve()
    try:
        with tempfile.TemporaryDirectory() as td:
            modelfile = Path(td) / "Modelfile"
            modelfile.write_text(f"FROM {gguf}\n", encoding="utf-8")
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
        if isinstance(entry, dict) and entry.get("gguf"):
            present[t] = (models_dir / entry["gguf"]).is_file()
    chosen_t, chosen = _best_bundled_for_tier(tier, bundled, models_dir)
    return {
        "dir": str(models_dir),
        "present": present,
        "chosen_tier": chosen_t,
        "chosen_name": chosen["name"] if chosen else None,
    }
