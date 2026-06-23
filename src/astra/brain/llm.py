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

Message = dict[str, str]  # {"role": "user"|"assistant"|"system", "content": "..."}


@dataclass
class BrainConfig:
    local_endpoint: str = "http://127.0.0.1:11434"  # Ollama por defecto
    local_model: str = "qwen2.5:3b-instruct"
    coder_model: str = "qwen2.5-coder:7b"
    temperature: float = 0.3
    top_p: float = 0.85
    cloud_boost_enabled: bool = False
    timeout_s: float = 120.0


class Brain:
    def __init__(self, config: BrainConfig, system_prompt: str) -> None:
        self.config = config
        self.system_prompt = system_prompt

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
            top_p=float(cfg.get("brain", "top_p", default=0.85)),
            cloud_boost_enabled=bool(cfg.get("brain", "cloud_boost", "enabled", default=False)),
        )
        return cls(bc, system_prompt)

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
            return f"[Astra] Tuve un problema al pensar: {exc}"

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
