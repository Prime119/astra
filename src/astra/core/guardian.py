"""
Capa Guardián — Candado de Dueño (Owner Lock) + Evidencia de Manipulación (Tamper-Lock).

Objetivo (del usuario): que solo el dueño pueda modificar el sistema; que una copia robada
sea inútil; y que si alguien altera el código sin autorización, el sistema se NIEGUE a
funcionar ("se rompe").

Realidad honesta:
- Ningún software es 100% irrompible. Estas capas elevan MUCHO la barrera, no la vuelven absoluta.
- Lo verdaderamente blindado: el rostro del dueño y las llaves viven SOLO en su dispositivo
  (carpeta de perfil, fuera del repositorio). Clonar el código de GitHub no da acceso a nada.

Capas que implementa este módulo:
1. **Manifiesto de integridad**: hash SHA-256 de cada archivo protegido (código + config + ética).
2. **Sello del dueño (seal)**: el dueño "sella" el estado bueno conocido. Vive en el perfil local,
   NO en el repo.
3. **Verificación**: al arrancar, si está sellado y el código no coincide con el sello, y el dueño
   NO está presente (rostro), el sistema entra en parálisis (se niega a operar).
4. **owner_present()**: hoy, marcador local / variable de entorno; a futuro, RECONOCIMIENTO FACIAL.

Modo desarrollo: si NO hay sello, no se aplica ninguna restricción (para poder programar).
El dueño activa la protección con `python -m astra --seal` (idealmente con su rostro verificado).
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from .config import PACKAGE_ROOT

# Archivos protegidos por el manifiesto de integridad.
PROTECTED_GLOBS = (
    "src/astra/**/*.py",
    "config/ethics_core.md",
    "config/astra.config.json",
    "config/editions/*.json",
)


def compute_manifest(root: Path | None = None) -> dict[str, str]:
    """Calcula el hash de cada archivo protegido. Clave = ruta relativa POSIX."""
    base = root or PACKAGE_ROOT
    manifest: dict[str, str] = {}
    for pattern in PROTECTED_GLOBS:
        for path in sorted(base.glob(pattern)):
            if path.is_file():
                rel = path.relative_to(base).as_posix()
                manifest[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    return manifest


def manifest_digest(manifest: dict[str, str]) -> str:
    """Hash único de todo el manifiesto (huella global del código)."""
    blob = json.dumps(manifest, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


@dataclass
class Guardian:
    profile_dir: Path
    root: Path = PACKAGE_ROOT

    # --- rutas locales (viven en el PERFIL, nunca en el repo) ---
    @property
    def seal_path(self) -> Path:
        return self.profile_dir / "guardian.seal"

    @property
    def owner_path(self) -> Path:
        # Plantilla biométrica del dueño (a futuro). Hoy, marcador de enrolamiento.
        return self.profile_dir / "owner.lock"

    @property
    def admins_path(self) -> Path:
        # Rostros adicionales autorizados por el dueño.
        return self.profile_dir / "admins.lock"

    # --- estado ---
    def is_sealed(self) -> bool:
        return self.seal_path.exists()

    def owner_enrolled(self) -> bool:
        return self.owner_path.exists()

    def current_digest(self) -> str:
        return manifest_digest(compute_manifest(self.root))

    def owner_present(self) -> bool:
        """
        ¿Está el dueño presente y verificado?
        FUTURO (Fase 5/7): coincidencia por RECONOCIMIENTO FACIAL en vivo (cámara).
        HOY (sin cámara): marcador local de sesión de dueño (variable de entorno ASTRA_OWNER=1).
        """
        import os
        return os.environ.get("ASTRA_OWNER") == "1"

    # --- acciones ---
    def seal(self) -> str:
        """El dueño sella el estado actual del código como 'bueno conocido'."""
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        digest = self.current_digest()
        payload = {"version": 1, "digest": digest}
        self.seal_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return digest

    def unseal(self) -> None:
        """Quita la protección (solo debería poder hacerlo el dueño presente)."""
        if self.seal_path.exists():
            self.seal_path.unlink()

    def verify(self) -> tuple[bool, str]:
        """
        Devuelve (ok, motivo).
        - No sellado -> ok (modo desarrollo).
        - Sellado y coincide -> ok.
        - Sellado y NO coincide -> ok solo si el dueño está presente; si no, FALLA (tamper).
        """
        if not self.is_sealed():
            return True, "sin sellar (modo desarrollo)"
        try:
            sealed = json.loads(self.seal_path.read_text(encoding="utf-8")).get("digest")
        except Exception:
            return False, "sello ilegible o corrupto"
        if self.current_digest() == sealed:
            return True, "integridad verificada"
        if self.owner_present():
            return True, "código alterado, pero dueño verificado: permitido"
        return False, "CÓDIGO ALTERADO sin autorización del dueño"

    def status(self) -> dict:
        ok, reason = self.verify()
        return {
            "sealed": self.is_sealed(),
            "owner_enrolled": self.owner_enrolled(),
            "owner_present": self.owner_present(),
            "integrity_ok": ok,
            "reason": reason,
        }
