"""
Capa 2 — Cerebro cognitivo multi-modelo.

Auto-detecta modelos instalados en Ollama y usa el más eficiente según la tarea:
- Conversación rápida → modelo pequeño (1.5b) para velocidad
- Preguntas complejas → modelo mediano (3b+) para profundidad
- Código → modelo coder especializado

La inteligencia REAL viene del aprendizaje continuo + personalidad + emociones,
no del tamaño del modelo. Un modelo pequeño con buen contexto supera a uno grande sin contexto.
"""
from __future__ import annotations

from dataclasses import dataclass


# Prioridad de modelos por TIPO DE TAREA (más rápido primero en cada categoría)
# Astra elegirá el primero que encuentre instalado en cada lista
MODELOS_CONVERSACION_RAPIDA = [
    "qwen2.5:1.5b-instruct",    # Ultra rápido (~1 seg)
    "qwen2.5:0.5b-instruct",    # Si existe, aún más rápido
]

MODELOS_CONVERSACION_PROFUNDA = [
    "astra-qwen2.5:3b",         # Custom de Astra (si existe, prioridad máxima)
    "qwen2.5:3b-instruct",      # Capaz y estable
    "qwen2.5:3b",               # Base
    "qwen2.5:7b-instruct",      # Si la PC aguanta
    "qwen2.5:14b-instruct",     # Para PCs potentes
]

MODELOS_CODIGO = [
    "qwen2.5-coder:3b",         # Especializado en código
    "qwen2.5-coder:1.5b",       # Coder rápido
    "qwen2.5-coder:7b",         # Coder potente
    "qwen2.5:3b-instruct",      # Fallback si no hay coder
]

Message = dict[str, str]


@dataclass
class BrainConfig:
    local_endpoint: str = "http://127.0.0.1:11434"
    modelo_rapido: str = "qwen2.5:1.5b-instruct"      # Para saludos/simple
    modelo_profundo: str = "qwen2.5:3b-instruct"      # Para preguntas complejas
    modelo_coder: str = "qwen2.5-coder:3b"            # Para código
    temperature: float = 0.4
    timeout_s: float = 120.0


class Brain:
    def __init__(self, config: BrainConfig, system_prompt: str) -> None:
        self.config = config
        self.system_prompt = system_prompt
        self._available_cache: bool | None = None
        self._installed_models: list[str] = []

    @classmethod
    def from_app_config(cls, cfg, system_prompt: str) -> "Brain":
        bc = BrainConfig(
            local_endpoint=cfg.get("brain", "local_endpoint", default="http://127.0.0.1:11434"),
            temperature=float(cfg.get("brain", "temperature", default=0.4)),
        )
        instance = cls(bc, system_prompt)
        instance._auto_configure()
        return instance

    def _auto_configure(self) -> None:
        """
        Auto-detecta modelos en Ollama y asigna el mejor para cada tarea.
        Prioridad: velocidad para conversación, especialización para código.
        """
        self._installed_models = self._fetch_models()
        
        if not self._installed_models:
            print("   ⚠️ No detecté modelos en Ollama. Usando defaults.")
            return
        
        print(f"   Modelos detectados: {', '.join(self._installed_models)}")
        
        # Asignar modelo rápido (conversación simple)
        self.config.modelo_rapido = self._encontrar_mejor(
            MODELOS_CONVERSACION_RAPIDA, fallback="qwen2.5:1.5b-instruct"
        )
        
        # Asignar modelo profundo (preguntas complejas)
        self.config.modelo_profundo = self._encontrar_mejor(
            MODELOS_CONVERSACION_PROFUNDA, fallback=self.config.modelo_rapido
        )
        
        # Asignar modelo coder
        self.config.modelo_coder = self._encontrar_mejor(
            MODELOS_CODIGO, fallback=self.config.modelo_profundo
        )
        
        print(f"   ✅ Rápido: {self.config.modelo_rapido}")
        print(f"   ✅ Profundo: {self.config.modelo_profundo}")
        print(f"   ✅ Código: {self.config.modelo_coder}")

    def _encontrar_mejor(self, prioridad: list[str], fallback: str) -> str:
        """Busca el primer modelo de la lista de prioridad que esté instalado."""
        for modelo in prioridad:
            for instalado in self._installed_models:
                # Match exacto o parcial (por tag)
                if modelo == instalado or modelo == instalado.split(":latest")[0]:
                    return instalado
                # Match por nombre base
                if modelo.replace("-instruct", "") in instalado:
                    return instalado
        # Si no encontró ninguno preferido, usar el fallback
        return fallback if fallback in self._installed_models else (
            self._installed_models[0] if self._installed_models else fallback
        )

    def _fetch_models(self) -> list[str]:
        """Consulta a Ollama qué modelos tiene instalados."""
        try:
            import httpx
            r = httpx.get(f"{self.config.local_endpoint}/api/tags", timeout=3.0)
            data = r.json()
            return [m.get("name", "") for m in data.get("models", [])]
        except Exception:
            return []

    # ---------------------------------------------------------------- estado
    def is_local_available(self) -> bool:
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
        if self._installed_models:
            return self._installed_models
        return self._fetch_models()

    def get_model_info(self) -> dict:
        return {
            "rapido": self.config.modelo_rapido,
            "profundo": self.config.modelo_profundo,
            "coder": self.config.modelo_coder,
            "instalados": self._installed_models,
        }

    # --------------------------------------------------------------- inferencia
    def chat(self, history: list[Message], *, coding: bool = False, 
             max_tokens: int = 0, deep: bool = False) -> str:
        """
        Envía la conversación al modelo local.
        - coding=True → usa modelo coder
        - deep=True → usa modelo profundo (preguntas complejas)
        - default → usa modelo rápido (velocidad)
        """
        if not self.is_local_available():
            return "No encuentro mi cerebro local. Verifica que Ollama esté corriendo."

        # Seleccionar modelo según tipo de tarea
        if coding:
            model = self.config.modelo_coder
        elif deep:
            model = self.config.modelo_profundo
        else:
            model = self.config.modelo_rapido

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
        """Atajo de un solo turno (sin historial). Usa modelo rápido."""
        return self.chat([{"role": "user", "content": prompt}], coding=coding)
