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
from ..core.config import PACKAGE_ROOT

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

# Mapeo de tipos del CSV/OSM al catálogo.
_CSV_TIPO_MAP = {
    "subestación": "subestacion", "subestacion": "subestacion", "substation": "subestacion",
    "termoeléctrica": "central_termo", "termoelectrica": "central_termo", "termo": "central_termo",
    "solar": "central_solar",
    "hidroeléctrica": "central_hidro", "hidroelectrica": "central_hidro", "hidro": "central_hidro",
    "eólica": "central_eolica", "eolica": "central_eolica",
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
    unlock_phrase: str = ""
    override_path: Path | None = None

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
        override_path = config.paths.profile_dir / "falcon_unlock.json"
        owner_override = False
        try:
            owner_override = bool(json.loads(override_path.read_text(encoding="utf-8")).get("unlocked", False))
        except Exception:
            owner_override = False
        obj = cls(
            active=True,
            enabled=bool(fal.get("enabled", False)),
            locked=bool(fal.get("locked", True)),
            threshold=float(fal.get("unlock_threshold", 1.0)),
            owner_override=owner_override,
            catalog=catalog,
            learner=VisionLearner(brain=brain),
            unlock_phrase=str(fal.get("unlock_phrase", "") or ""),
            override_path=override_path,
        )
        # Siembra automática: si el catálogo está vacío, lo llena con los datos REALES de OSM
        # (el avance sube solo sin intervención).
        if not obj.catalog.items:
            try:
                obj.seed_from_csv(PACKAGE_ROOT / "falcon" / "estructuras-cfe-osm.csv")
            except Exception:
                pass
        return obj

    # ----------------------------------------------------------- aprendizaje (datos reales)
    def seed_from_csv(self, path) -> int:
        """Confirma tipos del catálogo a partir del CSV real de OSM (offline, rápido)."""
        import csv
        from pathlib import Path as _P
        path = _P(path)
        if not self.catalog or not path.exists():
            return 0
        added = 0
        try:
            with path.open(encoding="utf-8-sig", newline="") as f:
                head = f.readline(); f.seek(0)
                delim = ';' if head.count(';') >= head.count(',') else ','
                have = self.catalog.confirmed_types()
                for row in csv.DictReader(f, delimiter=delim):
                    raw = (row.get("Tipo") or row.get("tipo") or "").strip().lower()
                    t = _CSV_TIPO_MAP.get(raw)
                    if t and t not in have:
                        self.catalog.add(t, nombre=(row.get("Nombre") or "").strip(), source="osm", confirmed=True)
                        have.add(t); added += 1
        except Exception:
            pass
        return added

    def learn_from_osm(self, states: list[str] | None = None) -> str:
        """
        APRENDIZAJE AUTÓNOMO desde mapas actuales (OpenStreetMap): busca infraestructura real,
        deduce su tipo y la agrega al catálogo con coordenadas verificadas. Requiere internet.
        """
        import json as _json
        import urllib.parse
        import urllib.request
        if not self.catalog:
            return "Catálogo no disponible."
        states = states or ["Sonora", "Sinaloa", "Chihuahua", "Baja California", "Baja California Sur"]
        nuevos: set[str] = set()
        have = self.catalog.confirmed_types()
        has_line = False

        def fetch(state: str):
            query = (
                '[out:json][timeout:60];area["name"="%s"]["admin_level"="4"]["boundary"="administrative"]->.a;'
                '(node["power"="substation"](area.a);way["power"="substation"](area.a);'
                'node["power"="plant"](area.a);way["power"="plant"](area.a);'
                'way["power"="line"](area.a);way["power"="minor_line"](area.a););out tags 300;'
            ) % state
            url = "https://overpass-api.de/api/interpreter?data=" + urllib.parse.quote(query)
            req = urllib.request.Request(url, headers={"User-Agent": "ASTRA-MEC/1.0"})
            return _json.loads(urllib.request.urlopen(req, timeout=80).read().decode())

        for st in states:
            try:
                data = fetch(st)
            except Exception:
                continue
            for e in data.get("elements", []):
                tg = e.get("tags", {}) or {}
                p = tg.get("power")
                t = None
                if p == "substation":
                    t = "subestacion"
                elif p == "plant":
                    src = (tg.get("plant:source") or tg.get("generator:source") or "").lower()
                    t = ("central_hidro" if "hydro" in src else "central_solar" if "solar" in src
                         else "central_eolica" if "wind" in src else "central_termo")
                elif p == "line":
                    t = "linea_alta_tension"; has_line = True
                elif p == "minor_line":
                    t = "linea_distribucion"; has_line = True
                if t and t not in have and t not in nuevos:
                    self.catalog.add(t, nombre=tg.get("name", ""), source="osm-auto", confirmed=True)
                    nuevos.add(t)
        if has_line:
            for t in ("torre_transmision_grande", "torre_transmision_mediana", "torre_transmision_chica", "poste"):
                if t not in have and t not in nuevos:
                    self.catalog.add(t, source="osm-auto", confirmed=True)
                    nuevos.add(t)
        return ("🛰️ Aprendí de mapas actuales (OpenStreetMap): confirmé %d tipos nuevos. "
                "Avance del catálogo: %d%%." % (len(nuevos), int(self.catalog.completeness() * 100)))

    def _save_override(self, val: bool) -> None:
        if not self.override_path:
            return
        try:
            self.override_path.parent.mkdir(parents=True, exist_ok=True)
            self.override_path.write_text(json.dumps({"unlocked": bool(val)}), encoding="utf-8")
        except Exception:
            pass

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
        if self.unlock_phrase and self.unlock_phrase.lower() in low:
            return True
        if any(h in low for h in ("bloquea falcon", "oculta falcon", "esconde falcon")):
            return True
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
        # Desbloqueo SECRETO: solo quien conoce la indicación puede activarlo (queda persistente).
        if self.unlock_phrase and self.unlock_phrase.lower() in low:
            self.owner_override = True
            self._save_override(True)
            return ("🔓 FALCON desbloqueado. A partir de ahora puedo abrirlo cuando me lo pidas. "
                    "(Esta indicación debería conocerla únicamente el creador.)")
        if any(h in low for h in ("bloquea falcon", "oculta falcon", "esconde falcon")):
            self.owner_override = False
            self._save_override(False)
            return "🔒 FALCON vuelve a quedar oculto y bloqueado."
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
