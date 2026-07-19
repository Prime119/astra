"""
Capa 2 — Cerebro cognitivo (llama.cpp).

Usa llama-server.exe como backend de inferencia (API compatible con OpenAI).
Más rápido y ligero que Ollama. Se ejecuta en http://127.0.0.1:8080

La inteligencia viene del aprendizaje continuo + personalidad + emociones.
"""
from __future__ import annotations

from dataclasses import dataclass


Message = dict[str, str]


@dataclass
class BrainConfig:
    local_endpoint: str = "http://127.0.0.1:8080"  # llama.cpp server
    temperature: float = 0.4
    timeout_s: float = 60.0


class Brain:
    def __init__(self, config: BrainConfig, system_prompt: str) -> None:
        self.config = config
        self.system_prompt = system_prompt
        self._available_cache: bool | None = None

    @classmethod
    def from_app_config(cls, cfg, system_prompt: str) -> "Brain":
        bc = BrainConfig(
            local_endpoint=cfg.get("brain", "local_endpoint", default="http://127.0.0.1:8080"),
            temperature=float(cfg.get("brain", "temperature", default=0.4)),
        )
        instance = cls(bc, system_prompt)
        # Verificar conexión
        if instance.is_local_available():
            print("   ✅ llama.cpp conectado")
        else:
            print("   ⚠️ llama.cpp no responde en puerto 8080. Ejecuta: llama-server.exe -m modelo.gguf -c 2048 --port 8080")
        return instance

    # ---------------------------------------------------------------- estado
    def is_local_available(self) -> bool:
        """Verifica si llama-server está corriendo."""
        if self._available_cache is not None:
            return self._available_cache
        try:
            import httpx
            r = httpx.get(f"{self.config.local_endpoint}/health", timeout=2.0)
            self._available_cache = r.status_code == 200
        except Exception:
            # Intentar endpoint alternativo
            try:
                import httpx
                r = httpx.get(f"{self.config.local_endpoint}/v1/models", timeout=2.0)
                self._available_cache = r.status_code == 200
            except Exception:
                self._available_cache = False
        return self._available_cache

    def available_models(self) -> list[str]:
        """Lista modelos disponibles en llama-server."""
        try:
            import httpx
            r = httpx.get(f"{self.config.local_endpoint}/v1/models", timeout=3.0)
            data = r.json()
            return [m.get("id", "") for m in data.get("data", [])]
        except Exception:
            return ["qwen2.5-1.5b"]

    def get_model_info(self) -> dict:
        return {
            "backend": "llama.cpp",
            "endpoint": self.config.local_endpoint,
            "modelos": self.available_models(),
        }

    # --------------------------------------------------------------- inferencia
    def chat(self, history: list[Message], *, coding: bool = False,
             max_tokens: int = 0, deep: bool = False) -> str:
        """
        Envía conversación a llama-server (API OpenAI compatible).
        """
        if not self.is_local_available():
            return "No encuentro llama.cpp. Ejecuta: llama-server.exe -m qwen2.5-1.5b.gguf -c 2048 --port 8080"

        messages: list[Message] = [{"role": "system", "content": self.system_prompt}]
        messages.extend(history)

        try:
            import httpx

            payload = {
                "messages": messages,
                "temperature": self.config.temperature,
                "stream": False,
            }
            if max_tokens > 0:
                payload["max_tokens"] = max_tokens

            r = httpx.post(
                f"{self.config.local_endpoint}/v1/chat/completions",
                json=payload,
                timeout=self.config.timeout_s,
            )
            r.raise_for_status()
            data = r.json()
            
            # Extraer respuesta (formato OpenAI)
            choices = data.get("choices", [])
            if choices:
                content = choices[0].get("message", {}).get("content", "")
                return content.strip() or "(sin respuesta)"
            return "(sin respuesta)"
        except Exception as exc:
            return f"Tuve un problema al pensar: {exc}"

    def think(self, prompt: str, *, coding: bool = False) -> str:
        """Atajo de un solo turno (sin historial)."""
        return self.chat([{"role": "user", "content": prompt}], coding=coding)
