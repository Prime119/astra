"""
Capa 0 — Núcleo Ético Inmutable.

Carga la "constitución" de Astra (config/ethics_core.md) en SOLO LECTURA y calcula
un hash de integridad. Si el archivo cambia, Astra lo detecta (telemetría Zero-Trust,
estilo Baymax/Zane) y puede entrar en parálisis preventiva.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from .config import ETHICS_CORE_PATH


@dataclass(frozen=True)
class Constitution:
    text: str
    sha256: str
    source: Path

    @property
    def short_hash(self) -> str:
        return self.sha256[:12]


def load_constitution(path: Path | None = None) -> Constitution:
    src = path or ETHICS_CORE_PATH
    text = src.read_text(encoding="utf-8")
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return Constitution(text=text, sha256=digest, source=src)


def verify_integrity(expected_hash: str | None = None) -> bool:
    """
    Verifica que el núcleo ético no haya sido alterado.
    Si `expected_hash` es None, solo confirma que el archivo carga correctamente.
    """
    try:
        current = load_constitution()
    except Exception:
        return False
    if expected_hash is None:
        return True
    return current.sha256 == expected_hash
