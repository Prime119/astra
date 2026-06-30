"""
Controlador del sistema FALCON para la IA MEC (SOLO edición CFE).

FALCON (mapa de infraestructura CFE + monitoreo) queda OCULTO/BLOQUEADO hasta que su
catálogo esté completo. Mientras tanto, si el usuario pide abrirlo, MEC responde —con tono
de ingeniero— que está en construcción y QUÉ falta por incorporar.

El catálogo se va llenando con ayuda de visión asistida (VisionLearner): el usuario aporta
mapas/fotos/videos y, si hay un modelo con visión, MEC PROPONE qué agregar y el dueño confirma.
(Honesto: no es aprendizaje 100% autónomo; reconocer equipo de CFE en imágenes requiere un
modelo de visión entrenado. Esto es la arquitectura + el flujo asistido.)
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from ..vision.learner import VisionLearner

# Catálogo OBJETIVO: todo lo que FALCON debe contener antes de poder mostrarse.
CATALOG_BLUEPRINT: dict[str, str] = {
    "subestacion": "Subestaciones eléctricas",
    "transformador": "Transformadores de potencia y distribución",
    "medidor": "Medidores de energía (incluye los de casas)",
    "central_hidro": "Centrales hidroeléctricas",
    "central_termo": "Centrales termoeléctricas",
    "central_solar": "Plantas solares (fotovoltaicas)",
    "central_eolica": "Centrales eólicas",
    "central_nuclear": "Centrales nucleares",
    "torre_transmision_chica": "Torres de transmisión pequeñas",
    "torre_transmision_mediana": "Torres de transmisión medianas",
    "torre_transmision_grande": "Torres de transmisión grandes",
    "linea_alta_tension": "Líneas de alta tensión",
    "linea_subtransmision": "Líneas de subtransmisión",
    "linea_distribucion": "Líneas de distribución",
    "poste": "Postes de distribución",
    "almacen": "Almacenes / bodegas",
    "oficina": "Oficinas / centros de atención",
    "interruptor": "Interruptores de potencia",
    "banco_capacitores": "Bancos de capacitores",
    "apartarrayos": "Apartarrayos",
}


@dataclass
class FalconCatalog:
    """Inventario aprendido de estructuras CFE, persistente en el perfil del usuario."""
    path: Path
    blueprint: dict[str, str] = field(default_factory=lambda: dict(CATALOG_BLUEPRINT))
    items: list[dict] = field(default_factory=list)

    def load(self) -> "FalconCatalog":
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self.items = data.get("items", [])
        except Exception:
            self.items = []
        return self

    def save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(
                json.dumps({"items": self.items}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass

    def add(self, tipo: str, nombre: str = "", lat: float | None = None,
            lon: float | None = None, source: str = "manual", confirmed: bool = False) -> None:
        self.items.append({
            "tipo": tipo, "nombre": nombre, "lat": lat, "lon": lon,
            "source": source, "confirmed": confirmed,
        })
        self.save()

    def confirmed_types(self) -> set[str]:
        return {it["tipo"] for it in self.items if it.get("confirmed") and it.get("tipo") in self.blueprint}

    def pending_types(self) -> list[str]:
        done = self.confirmed_types()
        return [t for t in self.blueprint if t not in done]

    def completeness(self) -> float:
        if not self.blueprint:
            return 1.0
        return len(self.confirmed_types()) / len(self.blueprint)


@dataclass
class Falcon:
    """Compuerta de acceso a FALCON desde la IA MEC."""
    active: bool = False           # solo activo en edición CFE
    enabled: bool = False          # habilitado por config
    locked: bool = True            # oculto/bloqueado hasta completar el catálogo
    threshold: float = 1.0         # fracción de catálogo requerida para desbloquear
    owner_override: bool = False   # el dueño puede forzar el desbloqueo
    catalog: FalconCatalog | None = None
    learner: VisionLearner | None = None

    @classmethod
    def from_config(cls, config, memory=None, brain=None) -> "Falcon":
        if getattr(config, "edition", "") != "cfe":
            return cls(active=False)
        fal = config.get("falcon", default={}) or {}
        blueprint = fal.get("catalog_blueprint")
        bp = {k: CATALOG_BLUEPRINT.get(k, k) for k in blueprint} if blueprint else dict(CATALOG_BLUEPRINT)
        catalog = FalconCatalog(
            path=config.paths.profile_dir / "falcon_catalog.json", blueprint=bp
        ).load()
        return cls(
            active=True,
            enabled=bool(fal.get("enabled", False)),
            locked=bool(fal.get("locked", True)),
            threshold=float(fal.get("unlock_threshold", 1.0)),
            catalog=catalog,
            learner=VisionLearner(brain=brain),
        )

    # ----------------------------------------------------------- intención
    _OPEN_HINTS = ("falcon", "abre el mapa", "abrir el mapa", "muéstrame el mapa",
                   "muestrame el mapa", "ver el mapa", "mapa 3d", "infraestructura cfe",
                   "mapa de cfe", "monitoreo visual")
    _STATUS_HINTS = ("estado de falcon", "avance de falcon", "cuánto falta", "cuanto falta",
                     "catálogo", "catalogo", "qué falta", "que falta")
    _LEARN_HINTS = ("aprende de", "analiza esta", "analiza la imagen", "agrega al catálogo",
                    "agrega al catalogo", "aprende esta")

    def is_falcon_intent(self, text: str) -> bool:
        if not self.active:
            return False
        low = text.lower()
        return any(h in low for h in (self._OPEN_HINTS + self._STATUS_HINTS + self._LEARN_HINTS))

    def is_ready(self) -> bool:
        if self.owner_override:
            return True
        if not self.enabled or self.locked:
            return False
        return self.catalog is not None and self.catalog.completeness() >= self.threshold

    # ----------------------------------------------------------- respuestas
    def handle(self, text: str) -> str:
        low = text.lower()
        if any(h in low for h in self._STATUS_HINTS):
            return self.report()
        if any(h in low for h in self._LEARN_HINTS):
            return (
                "Para aprender de una imagen/mapa necesito que me pases la ruta del archivo "
                "(o lo cargues por la interfaz). Lo analizo y te propongo qué agregar al catálogo; "
                "tú confirmas antes de guardarlo. " + self.learner.note()
            )
        # intención de abrir FALCON
        if self.is_ready():
            return "🛰️ Abriendo el sistema FALCON…"
        return self._locked_message()

    def _locked_message(self) -> str:
        pend = self.catalog.pending_types() if self.catalog else list(CATALOG_BLUEPRINT)
        pct = int((self.catalog.completeness() if self.catalog else 0) * 100)
        faltan = ", ".join(self.catalog.blueprint[t] for t in pend[:6]) if self.catalog else ""
        extra = f" (y {len(pend) - 6} más)" if len(pend) > 6 else ""
        return (
            "🔒 El sistema FALCON todavía está en construcción, así que no lo voy a abrir aún. "
            f"Avance del catálogo: {pct}%. "
            + (f"Aún faltan por incorporar: {faltan}{extra}. " if faltan else "")
            + "Cuando el catálogo esté completo (transformadores, medidores, plantas, torres "
            "chicas/medianas/grandes, almacenes, líneas, etc.), lo activo y te lo muestro."
        )

    def report(self) -> str:
        if not self.catalog:
            return "FALCON no está disponible en esta edición."
        pct = int(self.catalog.completeness() * 100)
        done = sorted(self.catalog.confirmed_types())
        pend = self.catalog.pending_types()
        return (
            f"📋 Catálogo FALCON — avance {pct}%.\n"
            f"Listo ({len(done)}): " + (", ".join(self.catalog.blueprint[t] for t in done) or "—") + "\n"
            f"Pendiente ({len(pend)}): " + (", ".join(self.catalog.blueprint[t] for t in pend) or "—")
        )

    def learn_from_image(self, image_path: str) -> str:
        """Analiza una imagen/mapa y PROPONE estructuras para el catálogo (el dueño confirma)."""
        if not self.learner:
            return "Visión no disponible."
        props = self.learner.analyze(image_path)
        if not props:
            return (
                "No pude reconocer estructuras automáticamente. " + self.learner.note()
            )
        nombres = ", ".join(p.get("tipo", "?") for p in props)
        for p in props:
            self.catalog.add(p.get("tipo", "desconocido"), source="vision", confirmed=False)
        return (
            f"Detecté posibles estructuras: {nombres}. Las dejé como PROPUESTA (sin confirmar). "
            "Confírmame cuáles son correctas para añadirlas al catálogo."
        )

    def status(self) -> dict:
        return {
            "active": self.active,
            "enabled": self.enabled,
            "locked": self.locked,
            "ready": self.is_ready(),
            "completeness": round(self.catalog.completeness(), 3) if self.catalog else 0.0,
            "pending": self.catalog.pending_types() if self.catalog else [],
        }
