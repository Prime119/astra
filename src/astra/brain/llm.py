"""
Capa 2 — Cerebro cognitivo.

Cliente real para un servidor LLM local (Ollama, API en http://127.0.0.1:11434).
Si el "Boost" está activado y hay internet, puede derivar a un modelo frontera en la nube
(Edge-Cloud híbrido, J.A.R.V.I.S.). Por defecto: SOLO local y offline.
"""
from __future__ import annotations

from dataclasses import dataclass, field


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

Message = dict[str, str]  # {"role": "user"|"assistant"|"system", "content": "..."}


@dataclass
class BrainConfig:
    local_endpoint: str = "http://127.0.0.1:11434"  # Ollama por defecto
    local_model: str = "qwen2.5:3b-instruct"
    coder_model: str = "qwen2.5-coder:7b"
    temperature: float = 0.3
    cloud_boost_enabled: bool = False
    timeout_s: float = 180.0  # 3 minutos (modelos pequeños en PCs con poca RAM tardan)


class Brain:
    def __init__(self, config: BrainConfig, system_prompt: str) -> None:
        self.config = config
        self.system_prompt = system_prompt
        self._available_cache: bool | None = None  # cache de disponibilidad

    @classmethod
    def from_app_config(cls, cfg, system_prompt: str) -> "Brain":
        tier = cfg.hardware.tier
        auto = bool(cfg.get("brain", "auto_scale_by_hardware", default=True))
        bc = BrainConfig(
            local_endpoint=cfg.get("brain", "local_endpoint", default="http://127.0.0.1:11434"),
            local_model=(MODEL_BY_TIER.get(tier) if auto else cfg.get("brain", "local_model"))
            or "qwen2.5:3b-instruct",
            coder_model=CODER_BY_TIER.get(tier, "qwen2.5-coder:7b"),
            temperature=float(cfg.get("brain", "temperature", default=0.3)),
            cloud_boost_enabled=bool(cfg.get("brain", "cloud_boost", "enabled", default=False)),
        )
        return cls(bc, system_prompt)

    # ---------------------------------------------------------------- estado
    def is_local_available(self) -> bool:
        """Comprueba si hay un servidor Ollama local respondiendo (con cache)."""
        if self._available_cache is not None:
            return self._available_cache
        try:
            import httpx
            r = httpx.get(f"{self.config.local_endpoint}/api/tags", timeout=2.0)
            self._available_cache = r.status_code == 200
        except Exception:
            self._available_cache = False
        return self._available_cache

    def available_models(self) -> list[str]:
        try:
            import httpx  # type: ignore

            r = httpx.get(f"{self.config.local_endpoint}/api/tags", timeout=3.0)
            data = r.json()
            return [m.get("name", "") for m in data.get("models", [])]
        except Exception:
            return []

    # --------------------------------------------------------------- inferencia
    def chat(self, history: list[Message], *, coding: bool = False, max_tokens: int = 0) -> str:
        """
        Envía la conversación al modelo local y devuelve la respuesta.
        `history` NO incluye el system prompt; se antepone aquí.
        max_tokens: si > 0, limita la respuesta (para respuestas rápidas).
        """
        if not self.is_local_available():
            return (
                "No encuentro mi cerebro local. Verifica que Ollama esté corriendo."
            )

        model = self.config.coder_model if coding else self.config.local_model
        messages: list[Message] = [{"role": "system", "content": self.system_prompt}]
        messages.extend(history)

        try:
            import httpx  # type: ignore

            options = {"temperature": self.config.temperature}
            if max_tokens > 0:
                options["num_predict"] = max_tokens

            payload = {
                "model": model,
                "messages": messages,
                "stream": False,
                "options": options,
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
            return f"Tuve un problema al pensar: {exc}"

    def think(self, prompt: str, *, coding: bool = False) -> str:
        """Atajo de un solo turno (sin historial)."""
        return self.chat([{"role": "user", "content": prompt}], coding=coding)
