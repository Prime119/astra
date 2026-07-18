"""
Capa 2 — Cerebro cognitivo.

Cliente para servidor LLM local (Ollama, API en http://127.0.0.1:11434).
Auto-detecta el hardware y selecciona el modelo MÁS RÁPIDO disponible.
La inteligencia viene del aprendizaje continuo, no del tamaño del modelo.

Prioridad: VELOCIDAD > profundidad
"""
from __future__ import annotations

from dataclasses import dataclass


# Modelos ordenados por VELOCIDAD (más rápido primero)
# Astra prioriza velocidad. La inteligencia viene del aprendizaje.
MODELOS_POR_VELOCIDAD = {
    "ligera": [
        "qwen2.5:1.5b-instruct",  # Ultra rápido, ideal para conversación
        "qwen2.5:3b-instruct",    # Rápido, más capaz
    ],
    "recomendada": [
        "qwen2.5:3b-instruct",    # Rápido en hardware medio
        "qwen2.5:7b-instruct",    # Más capaz si hay RAM
    ],
    "potente": [
        "qwen2.5:7b-instruct",    # Rápido con GPU
        "qwen2.5:14b-instruct",   # Máxima capacidad
    ],
}

# Todos los modelos que Astra puede usar (para auto-detección)
MODELOS_COMPATIBLES = [
    "qwen2.5:0.5b-instruct",
    "qwen2.5:1.5b-instruct",
    "qwen2.5:3b-instruct",
    "qwen2.5:7b-instruct",
    "qwen2.5:14b-instruct",
    "qwen2.5-coder:1.5b",
    "qwen2.5-coder:3b",
    "qwen2.5-coder:7b",
]

Message = dict[str, str]


@dataclass
class BrainConfig:
    local_endpoint: str = "http://127.0.0.1:11434"
    local_model: str = "qwen2.5:1.5b-instruct"  # Default: el más rápido
    coder_model: str = "qwen2.5-coder:3b"
    temperature: float = 0.4  # Un poco más creativo para conversación natural
    cloud_boost_enabled: bool = False
    timeout_s: float = 120.0  # 2 min (modelos pequeños son rápidos)


class Brain:
    def __init__(self, config: BrainConfig, system_prompt: str) -> None:
        self.config = config
        self.system_prompt = system_prompt
        self._available_cache: bool | None = None
        self._model_resolved: bool = False

    @classmethod
    def from_app_config(cls, cfg, system_prompt: str) -> "Brain":
        bc = BrainConfig(
            local_endpoint=cfg.get("brain", "local_endpoint", default="http://127.0.0.1:11434"),
            temperature=float(cfg.get("brain", "temperature", default=0.4)),
            cloud_boost_enabled=bool(cfg.get("brain", "cloud_boost", "enabled", default=False)),
        )
        instance = cls(bc, system_prompt)
        # Auto-detectar el mejor modelo al arrancar
        instance._auto_select_model(cfg.hardware.tier)
        return instance

    def _auto_select_model(self, tier: str) -> None:
        """
        Auto-selecciona el modelo MÁS RÁPIDO disponible en Ollama.
        Prioridad: velocidad > profundidad.
        La inteligencia viene del aprendizaje, no del tamaño del modelo.
        """
        # Obtener modelos instalados en Ollama
        installed = self.available_models()
        
        if not installed:
            # Ollama no responde o no hay modelos — usar default
            self.config.local_model = "qwen2.5:1.5b-instruct"
            self.config.coder_model = "qwen2.5-coder:3b"
            print(f"   ⚠️ No pude detectar modelos. Usando default: {self.config.local_model}")
            return
        
        print(f"   Modelos instalados en Ollama: {', '.join(installed)}")
        
        # Buscar el mejor modelo de conversación (prioridad: velocidad)
        preferidos = MODELOS_POR_VELOCIDAD.get(tier, MODELOS_POR_VELOCIDAD["ligera"])
        
        modelo_elegido = None
        for modelo in preferidos:
            # Buscar coincidencia parcial (Ollama puede tener :latest u otros tags)
            for instalado in installed:
                if modelo.split(":")[0] in instalado and modelo.split(":")[1].split("-")[0] in instalado:
                    modelo_elegido = instalado
                    break
                # Match exacto
                if modelo == instalado or modelo in instalado:
                    modelo_elegido = instalado
                    break
            if modelo_elegido:
                break
        
        # Si no encontró los preferidos, usar cualquier qwen instalado
        if not modelo_elegido:
            for instalado in installed:
                if "qwen" in instalado.lower():
                    modelo_elegido = instalado
                    break
        
        # Último fallback: primer modelo disponible
        if not modelo_elegido and installed:
            modelo_elegido = installed[0]
        
        if modelo_elegido:
            self.config.local_model = modelo_elegido
            print(f"   ✅ Modelo auto-seleccionado: {modelo_elegido} (tier: {tier}, prioridad: velocidad)")
        
        # Seleccionar modelo coder
        for instalado in installed:
            if "coder" in instalado.lower():
                self.config.coder_model = instalado
                break
        
        self._model_resolved = True

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
        """Lista los modelos instalados en Ollama."""
        try:
            import httpx
            r = httpx.get(f"{self.config.local_endpoint}/api/tags", timeout=3.0)
            data = r.json()
            return [m.get("name", "") for m in data.get("models", [])]
        except Exception:
            return []

    def get_model_info(self) -> dict:
        """Info del modelo actual para mostrar en status."""
        return {
            "modelo": self.config.local_model,
            "coder": self.config.coder_model,
            "endpoint": self.config.local_endpoint,
            "auto_detected": self._model_resolved,
        }

    # --------------------------------------------------------------- inferencia
    def chat(self, history: list[Message], *, coding: bool = False, max_tokens: int = 0) -> str:
        """
        Envía la conversación al modelo local y devuelve la respuesta.
        max_tokens: si > 0, limita la respuesta (para respuestas rápidas).
        """
        if not self.is_local_available():
            return "No encuentro mi cerebro local. Verifica que Ollama esté corriendo."

        model = self.config.coder_model if coding else self.config.local_model
        messages: list[Message] = [{"role": "system", "content": self.system_prompt}]
        messages.extend(history)

        try:
            import httpx

            options: dict = {"temperature": self.config.temperature}
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
        except Exception as exc:
            return f"Tuve un problema al pensar: {exc}"

    def think(self, prompt: str, *, coding: bool = False) -> str:
        """Atajo de un solo turno (sin historial)."""
        return self.chat([{"role": "user", "content": prompt}], coding=coding)
