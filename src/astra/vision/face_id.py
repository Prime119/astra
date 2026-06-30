"""
FACE ID del creador — reconocimiento facial para el Guardian.

Funciona parecido a Face ID: identifica por los RASGOS del rostro (no por accesorios), así que
te reconoce **con o sin lentes, con barba, con el cabello más largo**, etc. Y se **ADAPTA** a
cambios físicos normales: cuando hay una coincidencia muy fuerte, agrega esa muestra a tu perfil
(re-enrolamiento gradual), igual que Face ID con el tiempo.

Honesto:
- Requiere las librerías `face_recognition` (dlib) y `opencv-python`, más una **cámara**.
- Si no están instaladas o no hay cámara, degrada con elegancia: `verify()` devuelve None
  (= "no disponible") y el Guardian usa el respaldo de llave/sesión de dueño.
- El perfil del rostro vive SOLO en tu equipo (carpeta de perfil), nunca en el repositorio.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path


def _libs():
    try:
        import cv2  # type: ignore
        import face_recognition  # type: ignore
        import numpy as np  # type: ignore
        return cv2, face_recognition, np
    except Exception:
        return None, None, None


@dataclass
class FaceID:
    store_path: Path            # owner.lock (JSON con los encodings del creador)
    tolerance: float = 0.5      # distancia máx. para ACEPTAR (robusto a lentes/barba/cabello)
    strong: float = 0.38        # distancia para re-enrolamiento adaptativo (coincidencia fuerte)
    max_samples: int = 30

    # ---------------- disponibilidad / estado ----------------
    def available(self) -> bool:
        cv2, _, _ = _libs()
        return cv2 is not None

    def enrolled(self) -> bool:
        try:
            return bool(json.loads(self.store_path.read_text(encoding="utf-8")).get("encodings"))
        except Exception:
            return False

    def _load(self) -> list:
        try:
            return json.loads(self.store_path.read_text(encoding="utf-8")).get("encodings", [])
        except Exception:
            return []

    def _save(self, encs: list) -> None:
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self.store_path.write_text(
            json.dumps({"type": "face", "encodings": encs[-self.max_samples:]}, ensure_ascii=False),
            encoding="utf-8",
        )

    # ---------------- enrolamiento ----------------
    def enroll(self, samples: int = 8) -> str:
        cv2, fr, np = _libs()
        if cv2 is None:
            return ("Visión facial no disponible. Instala:  pip install opencv-python face_recognition")
        encs = self._load()
        nuevos = 0
        print("📸 Enrolando tu rostro. Mira a la cámara y muévete un poco; hazlo CON y SIN lentes "
              "para que te reconozca en ambos casos…")
        cam = cv2.VideoCapture(0)
        try:
            intentos = 0
            while nuevos < samples and intentos < samples * 10:
                intentos += 1
                ok, frame = cam.read()
                if not ok:
                    continue
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                locs = fr.face_locations(rgb)
                if locs:
                    e = fr.face_encodings(rgb, locs)
                    if e:
                        encs.append([float(x) for x in e[0]])
                        nuevos += 1
                        print(f"  muestra {nuevos}/{samples}")
                time.sleep(0.2)
        finally:
            cam.release()
        if nuevos == 0:
            return "No detecté tu rostro. Revisa la cámara e ilumina bien la cara."
        self._save(encs)
        return f"✅ Rostro del creador enrolado ({nuevos} muestras nuevas). El Guardian ya puede verificarte."

    # ---------------- verificación ----------------
    def _capture_encoding(self, fr, cv2, np, frames: int = 8):
        cam = cv2.VideoCapture(0)
        enc = None
        try:
            for _ in range(max(1, frames)):
                ok, frame = cam.read()
                if not ok:
                    continue
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                locs = fr.face_locations(rgb)
                if locs:
                    e = fr.face_encodings(rgb, locs)
                    if e:
                        enc = e[0]
                        break
                time.sleep(0.1)
        finally:
            cam.release()
        return enc

    def verify(self):
        """
        Devuelve True/False si hay cámara+modelo y rostro enrolado; None si no está disponible
        (para que el Guardian use su respaldo).
        """
        cv2, fr, np = _libs()
        if cv2 is None:
            return None
        known = self._load()
        if not known:
            return None
        enc = self._capture_encoding(fr, cv2, np)
        if enc is None:
            return False
        kn = np.array(known)
        dmin = float(np.linalg.norm(kn - enc, axis=1).min())
        if dmin <= self.tolerance:
            # Adaptación gradual (Face ID-like): si la coincidencia es muy fuerte, aprende esta muestra.
            if dmin <= self.strong and len(known) < self.max_samples:
                known.append([float(x) for x in enc])
                self._save(known)
            return True
        return False

    def note(self) -> str:
        if not self.available():
            return ("Face ID no disponible: instala `opencv-python` y `face_recognition` y conecta una "
                    "cámara. Mientras tanto, el Guardian usa la llave de dueño (ASTRA_OWNER=1).")
        if not self.enrolled():
            return "Cámara lista, pero aún no enrolas tu rostro. Ejecuta:  python -m astra --enroll-face"
        return "Face ID del creador activo."
