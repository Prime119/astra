"""
Configuración de Astra + detección de entorno (portátil vs residente) + hardware.

Reglas clave:
- `astra-base/`   -> SOLO LECTURA (programa + modelos). Nunca se escribe aquí.
- `astra-perfil/` -> ESCRIBIBLE (memoria, aprendizajes, config del usuario).
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# Raíz del proyecto = .../astra/ (sube desde src/astra/core/config.py)
# parents: [0]=core [1]=astra [2]=src [3]=raíz del proyecto
PACKAGE_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG_PATH = PACKAGE_ROOT / "config" / "astra.config.json"
ETHICS_CORE_PATH = PACKAGE_ROOT / "config" / "ethics_core.md"


@dataclass
class Hardware:
    """Recursos detectados, para auto-escalar el cerebro."""
    ram_gb: float = 0.0
    has_gpu: bool = False
    cpu_count: int = 0
    tier: str = "ligera"  # ligera | recomendada | potente

    @staticmethod
    def detect() -> "Hardware":
        ram_gb = 0.0
        cpu_count = os.cpu_count() or 1
        try:
            import psutil  # type: ignore
            ram_gb = round(psutil.virtual_memory().total / (1024 ** 3), 1)
        except Exception:
            ram_gb = 0.0

        has_gpu = _detect_gpu()

        # Selección de "tier" de modelo según recursos
        if ram_gb >= 24 and has_gpu:
            tier = "potente"
        elif ram_gb >= 12:
            tier = "recomendada"
        else:
            tier = "ligera"

        return Hardware(ram_gb=ram_gb, has_gpu=has_gpu, cpu_count=cpu_count, tier=tier)


def _detect_gpu() -> bool:
    """Detección best-effort de GPU dedicada (NVIDIA/AMD). No bloquea si falla."""
    # NVIDIA
    if any((Path(p) / "nvidia-smi").exists() for p in os.environ.get("PATH", "").split(os.pathsep) if p):
        return True
    # Variable típica en sistemas con CUDA
    if os.environ.get("CUDA_PATH"):
        return True
    return False


@dataclass
class Paths:
    """Rutas resueltas según el modo de ejecución."""
    base_dir: Path
    profile_dir: Path
    is_portable: bool

    def ensure_profile(self) -> None:
        """Crea el perfil escribible si no existe. NUNCA toca la base."""
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        (self.profile_dir / "memory").mkdir(exist_ok=True)
        (self.profile_dir / "projects").mkdir(exist_ok=True)


@dataclass
class Config:
    raw: dict[str, Any]
    hardware: Hardware
    paths: Paths

    # --- Accesos cómodos ---
    @property
    def name(self) -> str:
        return self.raw.get("identity", {}).get("name", "Astra")

    @property
    def wake_word(self) -> str:
        return self.raw.get("identity", {}).get("wake_word", "oye astra")

    def get(self, *keys: str, default: Any = None) -> Any:
        node: Any = self.raw
        for k in keys:
            if not isinstance(node, dict) or k not in node:
                return default
            node = node[k]
        return node


def _resolve_paths(raw: dict[str, Any]) -> Paths:
    """
    Decide si corremos en modo portátil (desde SSD) o residente.
    - portable: base y perfil viven JUNTO al ejecutable (en la SSD).
    - resident: el perfil vive en una carpeta de datos del usuario.
    """
    rt = raw.get("runtime", {})
    mode = rt.get("mode", "auto")
    base_name = rt.get("base_dir", "astra-base")
    profile_name = rt.get("profile_dir", "astra-perfil")

    # En portátil, todo cuelga de la raíz del proyecto (la SSD).
    portable_root = PACKAGE_ROOT
    is_portable = mode == "portable" or (mode == "auto" and _looks_portable())

    base_dir = portable_root  # los archivos del programa SON la base (solo lectura)
    if is_portable:
        profile_dir = portable_root / profile_name
    else:
        # Residente: perfil en datos del usuario (no deja la memoria mezclada con el programa)
        home = Path(os.environ.get("ASTRA_HOME", Path.home() / ".astra"))
        profile_dir = home / profile_name

    return Paths(base_dir=base_dir, profile_dir=profile_dir, is_portable=is_portable)


def _looks_portable() -> bool:
    """Heurística simple: si hay un marcador `PORTABLE` junto al programa, es portátil."""
    return (PACKAGE_ROOT / "PORTABLE").exists() or os.environ.get("ASTRA_PORTABLE") == "1"


def load_config(path: Path | None = None) -> Config:
    cfg_path = path or DEFAULT_CONFIG_PATH
    try:
        raw = json.loads(cfg_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raw = {}
    except json.JSONDecodeError as exc:
        print(f"[Astra] Config inválida en {cfg_path}: {exc}", file=sys.stderr)
        raw = {}

    hardware = Hardware.detect()
    paths = _resolve_paths(raw)
    paths.ensure_profile()

    return Config(raw=raw, hardware=hardware, paths=paths)
