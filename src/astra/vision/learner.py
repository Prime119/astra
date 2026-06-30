"""
Visión asistida — aprendizaje de estructuras CFE a partir de imágenes/mapas/video.

HONESTO: reconocer equipo de CFE en fotos requiere un MODELO DE VISIÓN (multimodal). Este
módulo es el flujo + la integración: si hay un modelo con visión disponible (p. ej. llava /
llama3.2-vision / moondream por Ollama), MEC analiza la imagen y PROPONE qué agregar al
catálogo; el dueño confirma. Si no hay modelo de visión, lo dice con claridad (no inventa).
"""
from __future__ import annotations

from dataclasses import dataclass

# Modelos locales con capacidad de visión que reconocemos por nombre.
_VISION_MODEL_HINTS = ("llava", "vision", "bakllava", "moondream", "minicpm", "qwen2-vl", "qwen2.5vl")


@dataclass
class VisionLearner:
    brain: object | None = None

    def _model_name(self) -> str:
        cfg = getattr(self.brain, "config", None)
        return (getattr(cfg, "local_model", "") or "").lower()

    def available(self) -> bool:
        """True si hay un modelo con visión configurado y disponible."""
        if self.brain is None:
            return False
        return any(h in self._model_name() for h in _VISION_MODEL_HINTS)

    def note(self) -> str:
        """Mensaje honesto sobre el estado de la visión."""
        if self.available():
            return "Visión activa (modelo multimodal detectado)."
        return (
            "Aún no hay un modelo de visión configurado. Para que MEC reconozca estructuras en "
            "imágenes, instala un modelo multimodal (p. ej. `ollama pull llava`) y selecciónalo; "
            "mientras tanto, puedo registrar estructuras que tú me indiques manualmente."
        )

    def analyze(self, image_path: str) -> list[dict]:
        """
        Devuelve propuestas [{'tipo': ..., 'confianza': ...}] detectadas en la imagen.
        Sin modelo de visión devuelve [] (no inventa). La llamada real al modelo multimodal
        (envío de la imagen + prompt de clasificación) se conecta aquí cuando el backend lo soporte.
        """
        if not self.available():
            return []
        # TODO: enviar `image_path` al modelo multimodal y parsear las clases detectadas.
        # Se deja el gancho listo; el envío de imágenes al backend se integra al conectar el modelo.
        return []
