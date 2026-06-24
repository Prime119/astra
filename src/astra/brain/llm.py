"""
Capa 2 — Cerebro cognitivo.

Cliente real para un servidor LLM local (Ollama, API en http://127.0.0.1:11434).
Si el "Boost" está activado y hay internet, puede derivar a un modelo frontera en la nube
(Edge-Cloud híbrido, J.A.R.V.I.S.). Por defecto: SOLO local y offline.

Si no hay modelo local disponible, opera en MODO BÁSICO con una degradación honesta
(regla 7: nunca finge): avisa que su cerebro completo no está activo, pero sigue util.
"""
from __future__ import annotations

from dataclasses import dataclass


# Modelos sugeridos por tier de hardware (auto-escala)
MODEL_BY_TIER = {
    "ligera": "qwen2.5:3b-instruct",
    "recomendada": "qwen2.5:7b-instruct",
    "potente": "qwen2.5:14b-instruct",
}
CODER_BY_TIER = {
    "ligera": "qwen2.5-coder:3b",
    "recomendada": "qwen2.5-coder:7b",
    "potente": "qwen2.5-coder:14b",
}

TIER_ORDER = ("ligera", "recomendada", "potente")

Message = dict[str, str]  # {"role": "user"|"assistant"|"system", "content": "..."}


def _list_ollama_models(endpoint: str, timeout: float = 3.0) -> list[str]:
    """Lista los modelos descargados en Ollama. [] si no responde o no hay httpx."""
    try:
        import httpx  # type: ignore
        r = httpx.get(f"{endpoint}/api/tags", timeout=timeout)
        if r.status_code == 200:
            return [m.get("name", "") for m in r.json().get("models", [])]
    except Exception:
        pass
    return []


def _ollama_reachable(endpoint: str, timeout: float = 2.0) -> bool:
    """True si el servidor de Ollama responde."""
    try:
        import httpx  # type: ignore
        return httpx.get(f"{endpoint}/api/tags", timeout=timeout).status_code == 200
    except Exception:
        return False


def choose_best(tier: str, available: list[str], table: dict[str, str]) -> str:
    """
    Auto-selección por dispositivo: el MEJOR modelo que (a) el hardware soporta (≤ tier) y
    (b) está realmente descargado. Si ninguno está descargado, devuelve el ideal del tier
    (para guiar el `ollama pull`).
    """
    idx = TIER_ORDER.index(tier) if tier in TIER_ORDER else 0
    for t in reversed(TIER_ORDER[: idx + 1]):  # del tope permitido hacia el más ligero
        tag = table.get(t)
        if tag and tag in available:
            return tag
    return table.get(tier, table.get("ligera", ""))


@dataclass
class BrainConfig:
    local_endpoint: str = "http://127.0.0.1:11434"  # Ollama por defecto
    local_model: str = "qwen2.5:3b-instruct"
    coder_model: str = "qwen2.5-coder:7b"
    temperature: float = 0.3
    top_p: float = 0.85
    cloud_boost_enabled: bool = False
    timeout_s: float = 300.0          # generoso: la 1ª inferencia carga el modelo en memoria
    keep_alive: str = "30m"           # mantiene el modelo cargado para respuestas rápidas


class Brain:
    def __init__(self, config: BrainConfig, system_prompt: str, name: str = "Astra") -> None:
        self.config = config
        self.system_prompt = system_prompt
        self.name = name

    @classmethod
    def from_app_config(cls, cfg, system_prompt: str) -> "Brain":
        tier = cfg.hardware.tier
        auto = bool(cfg.get("brain", "auto_scale_by_hardware", default=True))
        endpoint = cfg.get("brain", "local_endpoint", default="http://127.0.0.1:11434")
        available = _list_ollama_models(endpoint)
        reachable = _ollama_reachable(endpoint)

        local_model: str | None = None

        # 1) Preferir modelos INCLUIDOS con el programa (sin internet).
        bundled = cfg.get("brain", "bundled_models", default={}) or {}
        if isinstance(bundled, dict) and bundled:
            from pathlib import Path
            from .provisioner import ensure_bundled_model
            models_dir = Path(cfg.paths.base_dir) / cfg.get("brain", "bundled_models_dir", default="models")
            name, _msg = ensure_bundled_model(
                tier=tier, bundled=bundled, models_dir=models_dir,
                reachable=reachable, available=available,
            )
            if name:
                local_model = name
                if name not in available:
                    available = available + [name]

        # 2) Si no hay modelo incluido activable, usar los descargados en Ollama.
        if not local_model:
            if auto:
                local_model = choose_best(tier, available, MODEL_BY_TIER)
            else:
                local_model = cfg.get("brain", "local_model", default="qwen2.5:3b-instruct")

        # Modelo de código: el mejor disponible; si no hay, reutiliza el principal.
        coder_candidate = choose_best(tier, available, CODER_BY_TIER)
        coder_model = coder_candidate if coder_candidate in available else local_model

        bc = BrainConfig(
            local_endpoint=endpoint,
            local_model=local_model or "qwen2.5:3b-instruct",
            coder_model=coder_model or "qwen2.5-coder:7b",
            temperature=float(cfg.get("brain", "temperature", default=0.3)),
            top_p=float(cfg.get("brain", "top_p", default=0.85)),
            cloud_boost_enabled=bool(cfg.get("brain", "cloud_boost", "enabled", default=False)),
            timeout_s=float(cfg.get("brain", "timeout_s", default=300.0)),
        )
        return cls(bc, system_prompt, name=getattr(cfg, "name", "Astra"))

    # ---------------------------------------------------------------- estado
    def is_local_available(self) -> bool:
        """Comprueba si hay un servidor Ollama local respondiendo."""
        try:
            import httpx  # type: ignore

            r = httpx.get(f"{self.config.local_endpoint}/api/tags", timeout=2.0)
            return r.status_code == 200
        except Exception:
            return False

    def available_models(self) -> list[str]:
        try:
            import httpx  # type: ignore

            r = httpx.get(f"{self.config.local_endpoint}/api/tags", timeout=3.0)
            data = r.json()
            return [m.get("name", "") for m in data.get("models", [])]
        except Exception:
            return []

    # --------------------------------------------------------------- inferencia
    def chat(self, history: list[Message], *, coding: bool = False) -> str:
        """
        Envía la conversación al modelo local y devuelve la respuesta.
        `history` NO incluye el system prompt; se antepone aquí.
        Si no hay cerebro local, degrada con honestidad (modo básico).
        """
        if not self.is_local_available():
            return self._fallback_reply(history)

        model = self.config.coder_model if coding else self.config.local_model
        messages: list[Message] = [{"role": "system", "content": self.system_prompt}]
        messages.extend(history)

        try:
            import httpx  # type: ignore

            payload = {
                "model": model,
                "messages": messages,
                "stream": False,
                "keep_alive": self.config.keep_alive,
                "options": {
                    "temperature": self.config.temperature,
                    "top_p": self.config.top_p,
                },
            }
            r = httpx.post(
                f"{self.config.local_endpoint}/api/chat",
                json=payload,
                timeout=self.config.timeout_s,
            )
            r.raise_for_status()
            data = r.json()
            return (data.get("message", {}) or {}).get("content", "").strip() or "(sin respuesta)"
        except Exception as exc:  # degradación graciosa
            msg = str(exc).lower()
            if "timed out" in msg or "timeout" in msg or "read timed out" in msg:
                return (
                    f"[{self.name}] El modelo tardó demasiado (probablemente se estaba cargando en "
                    f"memoria por primera vez). Vuelve a intentar: la segunda vez es mucho más rápida. "
                    f"Tip: abre una terminal y ejecuta una vez `ollama run {self.config.local_model}` "
                    f"para precargarlo."
                )
            return f"[{self.name}] Tuve un problema al pensar: {exc}"

    def think(self, prompt: str, *, coding: bool = False) -> str:
        """Atajo de un solo turno (sin historial)."""
        return self.chat([{"role": "user", "content": prompt}], coding=coding)

    # ---------------------------------------------------------------- diagnóstico
    def diagnose(self) -> dict:
        """Revisa el estado de Ollama y qué modelos faltan (para el comando --check)."""
        reachable = self.is_local_available()
        models = self.available_models() if reachable else []
        needed = [self.config.local_model, self.config.coder_model]
        missing = [tag for tag in needed if tag not in models]
        return {
            "reachable": reachable,
            "endpoint": self.config.local_endpoint,
            "model": self.config.local_model,
            "coder_model": self.config.coder_model,
            "available": models,
            "missing": missing,
        }

    # ----------------------------------------------------------------- fallback
    def _fallback_reply(self, history: list[Message]) -> str:
        """
        Modo básico honesto (regla 7): el cerebro completo (LLM local) no está corriendo.
        No inventa respuestas: explica el estado y confirma que recibió el mensaje.
        """
        last = ""
        for msg in reversed(history):
            if msg.get("role") == "user":
                last = msg.get("content", "").strip()
                break
        eco = f' Tomé nota de: "{last}".' if last else ""
        return (
            "[Modo básico] Mi cerebro completo (modelo local Ollama) no está activo ahora mismo, "
            "así que no puedo razonar a fondo todavía." + eco +
            "\nPara activarlo: 1) instala y abre Ollama, 2) ejecuta  "
            f"`ollama pull {self.config.local_model}`.  Verifica el estado con  `python -m astra --check`. "
            "Mientras tanto, el núcleo de seguridad y la memoria siguen operativos."
        )
