"""
Capa 2 — Cerebro cognitivo (llama.cpp) con Multi-Modelo.

Usa llama-server.exe como backend de inferencia (API compatible con OpenAI).
Más rápido y ligero que Ollama. Se ejecuta en http://127.0.0.1:8080

NUEVO: Soporte multi-modelo con routing inteligente.
- Auto-detecta qué modelo usar según la tarea
- Hot-swap de modelos via ModelManager
- Fallback graceful si el modelo óptimo no está disponible

La inteligencia viene del aprendizaje continuo + personalidad + emociones.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


Message = dict[str, str]


@dataclass
class BrainConfig:
    local_endpoint: str = "http://127.0.0.1:8080"  # llama.cpp server
    temperature: float = 0.4
    timeout_s: float = 60.0
    auto_route: bool = True  # Habilitar routing automático de modelos


class Brain:
    def __init__(self, config: BrainConfig, system_prompt: str) -> None:
        self.config = config
        self.system_prompt = system_prompt
        self._available_cache: bool | None = None
        self._router = None
        self._model_manager = None
        self._current_model_id: str = ""

        # Inicializar router si está disponible
        self._init_router()

    def _init_router(self):
        """Inicializa el ModelRouter y ModelManager si están disponibles."""
        try:
            from astra.brain.model_router import ModelRouter
            from installer.model_manager import get_model_manager

            self._model_manager = get_model_manager()
            installed = self._model_manager.get_installed_models()

            self._router = ModelRouter(installed_models=installed)

            # Registrar modelo activo actual
            server_status = self._model_manager.get_server_status()
            if server_status.get("model"):
                self._current_model_id = server_status["model"]
                self._router.set_current_model(self._current_model_id)

        except ImportError:
            # Router/Manager no disponibles (modo legacy sin installer)
            self._router = None
            self._model_manager = None
        except Exception as e:
            print(f"   ⚠️ Router no inicializado: {e}")
            self._router = None

    @classmethod
    def from_app_config(cls, cfg, system_prompt: str) -> "Brain":
        bc = BrainConfig(
            local_endpoint=cfg.get("brain", "local_endpoint", default="http://127.0.0.1:8080"),
            temperature=float(cfg.get("brain", "temperature", default=0.4)),
            auto_route=cfg.get("brain", "local_model", default="auto") == "auto",
        )
        instance = cls(bc, system_prompt)
        # Verificar conexión
        if instance.is_local_available():
            print("   ✅ llama.cpp conectado")
            if instance._router:
                installed = instance._model_manager.get_installed_models() if instance._model_manager else []
                print(f"   🧠 Router activo — {len(installed)} modelo(s) disponibles")
        else:
            print("   ⚠️ llama.cpp no responde en puerto 8080.")
            print("      Ejecuta: llama-server.exe -m modelo.gguf -c 2048 --port 8080")
            # Intentar auto-iniciar si ModelManager disponible
            if instance._model_manager:
                instance._try_auto_start_server()
        return instance

    def _try_auto_start_server(self) -> bool:
        """Intenta iniciar llama-server automáticamente con el mejor modelo."""
        if not self._model_manager:
            return False

        installed = self._model_manager.get_installed_models()
        if not installed:
            print("   ❌ No hay modelos instalados. Ejecuta el setup primero.")
            return False

        # Usar el modelo más pequeño para arranque rápido
        quick_model = None
        for m in ["qwen2.5-1.5b-instruct", "qwen2.5-3b-instruct"]:
            if m in installed:
                quick_model = m
                break
        if not quick_model:
            quick_model = installed[0]

        print(f"   🚀 Auto-iniciando llama-server con {quick_model}...")
        success = self._model_manager.start_server(model_id=quick_model)
        if success:
            self._current_model_id = quick_model
            if self._router:
                self._router.set_current_model(quick_model)
            self._available_cache = True
            print(f"   ✅ Servidor iniciado con {quick_model}")
        return success

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
        """Lista modelos disponibles (instalados en disco)."""
        if self._model_manager:
            return self._model_manager.get_installed_models()
        # Fallback: preguntar al servidor
        try:
            import httpx
            r = httpx.get(f"{self.config.local_endpoint}/v1/models", timeout=3.0)
            data = r.json()
            return [m.get("id", "") for m in data.get("data", [])]
        except Exception:
            return ["qwen2.5-1.5b"]

    def get_model_info(self) -> dict:
        """Información del sistema de modelos."""
        info = {
            "backend": "llama.cpp",
            "endpoint": self.config.local_endpoint,
            "modelos_instalados": self.available_models(),
            "modelo_activo": self._current_model_id,
            "auto_route": self.config.auto_route,
        }
        if self._router:
            info["router_stats"] = self._router.get_stats()
        return info

    def get_system_prompt(self) -> str:
        """Devuelve el system prompt actual."""
        return self.system_prompt

    @property
    def model_name(self) -> str:
        """Nombre del modelo actualmente cargado."""
        return self._current_model_id or "qwen2.5-1.5b-instruct"

    # ---------------------------------------------------------------- routing
    def _route_and_switch(self, user_text: str, has_image: bool = False) -> Optional[str]:
        """
        Usa el router para decidir el modelo óptimo y hace switch si necesario.
        
        Returns:
            model_id seleccionado, o None si no se pudo cambiar
        """
        if not self._router or not self.config.auto_route:
            return self._current_model_id or None

        decision = self._router.route(user_text, has_image=has_image)

        # Verificar si vale la pena hacer switch
        if decision.needs_switch and self._router.should_switch_model(decision.model_id):
            if self._model_manager:
                print(f"   🔄 Switch: {self._current_model_id} → {decision.model_id} ({decision.reason})")
                success = self._model_manager.switch_model(decision.model_id)
                if success:
                    self._current_model_id = decision.model_id
                    self._router.set_current_model(decision.model_id)
                    self._available_cache = True
                else:
                    print(f"   ⚠️ Switch fallido, continuando con {self._current_model_id}")
        elif not self._current_model_id and decision.model_id:
            # No hay modelo cargado aún — cargar el decidido
            self._current_model_id = decision.model_id

        return decision.model_id

    # --------------------------------------------------------------- inferencia
    def chat(self, history: list[Message], *, coding: bool = False,
             max_tokens: int = 0, deep: bool = False,
             has_image: bool = False) -> str:
        """
        Envía conversación a llama-server (API OpenAI compatible).
        
        Con auto_route=True, selecciona automáticamente el mejor modelo.
        """
        if not self.is_local_available():
            # Intentar auto-start
            if self._try_auto_start_server():
                pass  # Servidor iniciado
            else:
                return ("No encuentro llama.cpp. Ejecuta: "
                        "llama-server.exe -m modelo.gguf -c 2048 --port 8080")

        # Routing inteligente: decidir modelo según el último mensaje del usuario
        if history and self.config.auto_route:
            last_user_msg = ""
            for msg in reversed(history):
                if msg.get("role") == "user":
                    last_user_msg = msg.get("content", "")
                    break
            if last_user_msg:
                self._route_and_switch(last_user_msg, has_image=has_image)

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
            elif deep:
                payload["max_tokens"] = 512  # Más tokens para respuestas profundas

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

    def think_with_model(self, prompt: str, model_id: str) -> str:
        """Fuerza uso de un modelo específico (ignora router)."""
        # Guardar estado
        old_auto = self.config.auto_route
        old_model = self._current_model_id

        try:
            self.config.auto_route = False
            if self._model_manager and model_id != self._current_model_id:
                self._model_manager.switch_model(model_id)
                self._current_model_id = model_id

            result = self.think(prompt)
            return result
        finally:
            self.config.auto_route = old_auto
            # No revertir el modelo — se queda el último usado

    # ---------------------------------------------------------------- shutdown
    def shutdown(self):
        """Detiene el servidor llama.cpp (para cierre limpio)."""
        if self._model_manager:
            self._model_manager.stop_server()
            self._available_cache = False
