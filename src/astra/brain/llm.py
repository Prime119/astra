"""
Capa 2 — Cerebro cognitivo.

Se conecta a un servidor LLM local (llama.cpp / Ollama, API compatible con OpenAI).
Si está activado el "Boost" y hay internet, puede derivar a un modelo frontera en la nube
(Edge-Cloud híbrido, J.A.R.V.I.S.). Por defecto: SOLO local y offline.

NOTA (Fase 0): este módulo define la interfaz y la lógica de fallback. La inferencia real
requiere un servidor LLM local corriendo en la PC del usuario (se configura en Fase 1).
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


@dataclass
class BrainConfig:
    local_endpoint: str = "http://127.0.0.1:11434"  # Ollama por defecto
    local_model: str = "qwen2.5:3b-instruct"
    coder_model: str = "qwen2.5-coder:7b"
    temperature: float = 0.3
    cloud_boost_enabled: bool = False


class Brain:
    def __init__(self, config: BrainConfig, system_prompt: str) -> None:
        self.config = config
        self.system_prompt = system_prompt

    @classmethod
    def from_app_config(cls, cfg, system_prompt: str) -> "Brain":
        tier = cfg.hardware.tier
        bc = BrainConfig(
            local_model=(
                cfg.get("brain", "local_model")
                if not cfg.get("brain", "auto_scale_by_hardware", default=True)
                else MODEL_BY_TIER.get(tier, "qwen2.5:3b-instruct")
            ),
            coder_model=CODER_BY_TIER.get(tier, "qwen2.5-coder:7b"),
            temperature=float(cfg.get("brain", "temperature", default=0.3)),
            cloud_boost_enabled=bool(cfg.get("brain", "cloud_boost", "enabled", default=False)),
        )
        return cls(bc, system_prompt)

    def is_local_available(self) -> bool:
        """Comprueba si hay un servidor LLM local respondiendo."""
        try:
            import httpx  # type: ignore
            r = httpx.get(f"{self.config.local_endpoint}/api/tags", timeout=2.0)
            return r.status_code == 200
        except Exception:
            return False

    def think(self, prompt: str, *, coding: bool = False) -> str:
        """
        Genera una respuesta. Estrategia:
        1. Si el boost está activo y hay internet -> nube (nivel frontera).
        2. Si no -> modelo local.
        3. Si no hay local -> mensaje de degradación graciosa.
        """
        if not self.is_local_available():
            return (
                "[Astra] Aún no tengo un cerebro local en marcha. "
                "En la Fase 1 conectaremos el modelo (Ollama/llama.cpp) en tu PC. "
                "Por ahora opero solo a nivel de estructura."
            )
        # Inferencia real se implementa en Fase 1 (cliente chat compatible OpenAI/Ollama).
        model = self.config.coder_model if coding else self.config.local_model
        return f"[Astra:{model}] (inferencia local pendiente de Fase 1)"
