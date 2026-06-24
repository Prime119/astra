"""
Configuración de Astra + detección de entorno (portátil vs residente) + hardware
+ sistema de EDICIONES (Full / CFE).

Reglas clave:
- `astra-base/`   -> SOLO LECTURA (programa + modelos). Nunca se escribe aquí.
- `astra-perfil/` -> ESCRIBIBLE (memoria, aprendizajes, config del usuario).

Ediciones:
- La configuración base vive en `config/astra.config.json`.
- Cada edición (`config/editions/<id>.json`) se FUSIONA encima de la base.
- Un solo núcleo de código; el comportamiento cambia por configuración.
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


# Raíz del proyecto = .../astra/ (sube desde src/astra/core/config.py)
# parents: [0]=core [1]=astra [2]=src [3]=raíz del proyecto
PACKAGE_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG_PATH = PACKAGE_ROOT / "config" / "astra.config.json"
ETHICS_CORE_PATH = PACKAGE_ROOT / "config" / "ethics_core.md"
EDITIONS_DIR = PACKAGE_ROOT / "config" / "editions"

DEFAULT_EDITION = "full"
VALID_EDITIONS = ("full", "cfe")


@dataclass
class Hardware:
    """Recursos detectados, para auto-escalar el cerebro."""
    ram_gb: float = 0.0
    has_gpu: bool = False
    cpu_count: int = 0
    tier: str = "ligera"  # ligera | recomendada | potente

    @staticmethod
    def detect() -> "Hardware":
        ram_gb = Hardware._detect_ram_gb()
        cpu_count = os.cpu_count() or 1
        has_gpu = _detect_gpu()

        # Selección de "tier" según RAM y GPU (umbrales conservadores: el modelo debe caber holgado).
        if (ram_gb >= 30) or (has_gpu and ram_gb >= 24):
            tier = "potente"      # 14B
        elif ram_gb >= 15:
            tier = "recomendada"  # 7B
        else:
            tier = "ligera"       # 3B (p. ej. laptops de 8 GB)

        return Hardware(ram_gb=ram_gb, has_gpu=has_gpu, cpu_count=cpu_count, tier=tier)

    @staticmethod
    def _detect_ram_gb() -> float:
        """RAM total en GB. Funciona aunque NO esté psutil (Windows via ctypes, Unix via sysconf)."""
        # 1) psutil (si está)
        try:
            import psutil  # type: ignore
            return round(psutil.virtual_memory().total / (1024 ** 3), 1)
        except Exception:
            pass
        # 2) Windows (ctypes)
        try:
            import ctypes

            class _MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            stat = _MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(_MEMORYSTATUSEX)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))  # type: ignore[attr-defined]
            return round(stat.ullTotalPhys / (1024 ** 3), 1)
        except Exception:
            pass
        # 3) Unix (Linux/Mac)
        try:
            return round(os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / (1024 ** 3), 1)
        except Exception:
            return 0.0


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
    edition: str = DEFAULT_EDITION

    # --- Accesos cómodos ---
    @property
    def name(self) -> str:
        return self.raw.get("identity", {}).get("name", "Astra")

    @property
    def edition_name(self) -> str:
        return self.raw.get("edition", {}).get("name", "ASTRA")

    @property
    def persona(self) -> str:
        return self.raw.get("edition", {}).get("persona", "general")

    @property
    def domain_focus(self) -> str:
        return self.raw.get("edition", {}).get("domain_focus", "none")

    @property
    def wake_word(self) -> str:
        return self.raw.get("identity", {}).get("wake_word", "oye astra")

    @property
    def capabilities(self) -> dict[str, bool]:
        return self.raw.get("capabilities", {})

    def is_enabled(self, capability: str) -> bool:
        """True si la capacidad está habilitada en la edición activa."""
        return bool(self.capabilities.get(capability, False))

    def get(self, *keys: str, default: Any = None) -> Any:
        node: Any = self.raw
        for k in keys:
            if not isinstance(node, dict) or k not in node:
                return default
            node = node[k]
        return node


def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    """Fusiona `overlay` sobre `base` recursivamente (sin mutar los originales)."""
    result = dict(base)
    for key, value in overlay.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _resolve_edition(edition: str | None) -> str:
    """Resuelve la edición: argumento > variable de entorno > por defecto."""
    chosen = (edition or os.environ.get("ASTRA_EDITION") or DEFAULT_EDITION).lower().strip()
    if chosen not in VALID_EDITIONS:
        print(f"[Astra] Edición '{chosen}' desconocida; uso '{DEFAULT_EDITION}'.", file=sys.stderr)
        chosen = DEFAULT_EDITION
    return chosen


def _load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as exc:
        print(f"[Astra] Config inválida en {path}: {exc}", file=sys.stderr)
        return {}


def _resolve_paths(raw: dict[str, Any], edition: str) -> Paths:
    """
    Decide si corremos en modo portátil (desde SSD) o residente.
    - portable: base y perfil viven JUNTO al ejecutable (en la SSD).
    - resident: el perfil vive en una carpeta de datos del usuario.

    El perfil se separa por edición para que ASTRA Full y ASTRA CFE no mezclen su memoria.
    """
    rt = raw.get("runtime", {})
    mode = rt.get("mode", "auto")
    profile_name = rt.get("profile_dir", "astra-perfil")
    # Cada edición tiene su propio perfil (memoria aislada).
    profile_name = f"{profile_name}-{edition}"

    portable_root = PACKAGE_ROOT
    is_portable = mode == "portable" or (mode == "auto" and _looks_portable())

    base_dir = portable_root  # los archivos del programa SON la base (solo lectura)
    if is_portable:
        profile_dir = portable_root / profile_name
    else:
        home = Path(os.environ.get("ASTRA_HOME", Path.home() / ".astra"))
        profile_dir = home / profile_name

    return Paths(base_dir=base_dir, profile_dir=profile_dir, is_portable=is_portable)


def _looks_portable() -> bool:
    """Heurística simple: si hay un marcador `PORTABLE` junto al programa, es portátil."""
    return (PACKAGE_ROOT / "PORTABLE").exists() or os.environ.get("ASTRA_PORTABLE") == "1"


def load_config(path: Path | None = None, edition: str | None = None) -> Config:
    """Carga la config base y fusiona encima el perfil de la edición elegida."""
    cfg_path = path or DEFAULT_CONFIG_PATH
    raw = _load_json(cfg_path)

    chosen = _resolve_edition(edition)
    overlay = _load_json(EDITIONS_DIR / f"{chosen}.json")
    if overlay:
        raw = _deep_merge(raw, overlay)

    hardware = Hardware.detect()
    paths = _resolve_paths(raw, chosen)
    paths.ensure_profile()

    return Config(raw=raw, hardware=hardware, paths=paths, edition=chosen)
