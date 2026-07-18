"""
Orquestador — une todas las capas y aplica el flujo de seguridad.

Pipeline (inspirado en F.R.I.D.A.Y.):
  entrada -> personalidad/contexto -> cerebro propone -> AUDITOR revisa
          -> (si OK) ejecutor actúa / responde -> memoria registra
          -> aprendizaje extrae hechos -> evolución continua
"""
from __future__ import annotations

import traceback
from dataclasses import dataclass, field

from ..brain.llm import Brain
from ..memory.store import Memory
from ..memory.learning import LearningEngine
from .auditor import Auditor, Risk
from .config import Config, load_config
from .constitution import Constitution, load_constitution
from .emotions import EmotionalEngine
from .personality import Personality


# Palabras que sugieren tarea de programación -> usar el modelo "coder"
CODING_HINTS = (
    "código", "codigo", "programa", "función", "funcion", "script", "python",
    "javascript", "java", "html", "css", "bug", "error en el código", "compilar",
)

MAX_HISTORY_TURNS = 8  # límite reducido para velocidad (8 turnos = 16 mensajes)


@dataclass
class Astra:
    config: Config
    constitution: Constitution
    personality: Personality
    auditor: Auditor
    memory: Memory
    learning: LearningEngine
    emotions: EmotionalEngine
    brain: Brain
    history: list[dict] = field(default_factory=list)

    @classmethod
    def boot(cls) -> "Astra":
        config = load_config()
        constitution = load_constitution()
        personality = Personality.from_config(config.get("personality", default={}))
        personality.clamp()
        auditor = Auditor(constitution_hash=constitution.sha256)
        memory = Memory(profile_dir=config.paths.profile_dir)
        learning = LearningEngine(profile_dir=config.paths.profile_dir)
        emotions = EmotionalEngine(profile_dir=config.paths.profile_dir)

        system_prompt = _build_system_prompt(constitution, personality, emotions)
        brain = Brain.from_app_config(config, system_prompt=system_prompt)

        instance = cls(
            config=config,
            constitution=constitution,
            personality=personality,
            auditor=auditor,
            memory=memory,
            learning=learning,
            emotions=emotions,
            brain=brain,
        )
        # Cargar historial previo (best-effort, no crashea si falla)
        instance._load_recent_history()
        return instance

    def _load_recent_history(self) -> None:
        """Carga solo las últimas 3 conversaciones para no saturar el contexto."""
        try:
            recent = self.memory.get_recent_conversations(limit=3)
            for entry in recent:
                self.history.append({"role": "user", "content": entry["user"]})
                self.history.append({"role": "assistant", "content": entry["assistant"]})
        except Exception:
            pass

    def status(self) -> dict:
        try:
            learnings_count = self.learning.count()
        except Exception:
            learnings_count = 0
        try:
            memory_episodes = self.memory.episode_count()
        except Exception:
            memory_episodes = 0
        try:
            emotional_status = self.emotions.get_status()
        except Exception:
            emotional_status = {"emocion": "neutral", "intensidad": 50}
            
        return {
            "name": self.config.name,
            "version_constitution": self.constitution.short_hash,
            "mode": "portátil" if self.config.paths.is_portable else "residente",
            "hardware": {
                "ram_gb": self.config.hardware.ram_gb,
                "gpu": self.config.hardware.has_gpu,
                "tier": self.config.hardware.tier,
            },
            "profile_dir": str(self.config.paths.profile_dir),
            "brain_local_online": self.brain.is_local_available(),
            "personality": {
                "honesty": self.personality.honesty,
                "humor": self.personality.humor,
                "proactivity": self.personality.proactivity,
            },
            "emotions": emotional_status,
            "learnings_count": learnings_count,
            "memory_episodes": memory_episodes,
        }

    def handle(self, user_text: str) -> str:
        """Procesa una entrada de texto pasando por el auditor y manteniendo el hilo."""
        # Auditoría de seguridad
        try:
            verdict = self.auditor.review_action(user_text)
            if verdict.risk == Risk.BLOCK:
                return f"No puedo hacer eso. {verdict.reason}"
            if verdict.risk == Risk.CONFIRM:
                self.memory.remember("accion_pendiente", user_text)
                return f"{verdict.reason} ¿Confirmas que proceda? (sí/no)"
        except Exception:
            pass

        coding = any(h in user_text.lower() for h in CODING_HINTS)
        
        # Detectar complejidad para limitar tokens (respuestas más rápidas)
        max_tokens = self._estimar_tokens(user_text)
        
        # Detectar si necesita pensamiento profundo
        deep = self._necesita_profundidad(user_text)

        # Actualizar system prompt con estado emocional actual
        try:
            self.brain.system_prompt = _build_system_prompt(
                self.constitution, self.personality, self.emotions
            )
        except Exception:
            pass

        # Hilo de conversación (memoria de trabajo, volátil)
        self.history.append({"role": "user", "content": user_text})
        response = self.brain.chat(self.history, coding=coding, max_tokens=max_tokens, deep=deep)
        self.history.append({"role": "assistant", "content": response})
        self._trim_history()

        # Procesar emociones DESPUÉS de la respuesta (best-effort)
        try:
            self.emotions.procesar_interaccion(user_text, response)
        except Exception:
            pass

        # Memoria persistente (best-effort, no bloquea la respuesta)
        try:
            self.memory.log_episode("conversacion", user_text)
            self.memory.save_conversation(user_text, response)
        except Exception:
            pass

        return self.personality.flag_figurative(response)

    def _estimar_tokens(self, texto: str) -> int:
        """
        Estima cuántos tokens necesita la respuesta según la complejidad.
        """
        t = texto.lower().strip()
        largo = len(t)
        
        simples = ["hola", "cómo estás", "qué tal", "hey", "buenas", "gracias",
                   "ok", "está bien", "vale", "sí", "no", "adiós", "bye",
                   "qué hora es", "qué día es", "cómo te llamas"]
        if any(t.startswith(s) or t == s for s in simples) or largo < 10:
            return 60
        if largo < 40 and "?" in t:
            return 120
        if largo < 80:
            return 200
        return 0

    def _necesita_profundidad(self, texto: str) -> bool:
        """
        Detecta si la pregunta requiere pensamiento profundo (modelo grande).
        Preguntas simples usan el modelo rápido; complejas el profundo.
        """
        t = texto.lower()
        largo = len(t)
        
        # Preguntas complejas que necesitan más capacidad
        deep_triggers = [
            "explica", "explícame", "por qué", "cómo funciona", "analiza",
            "compara", "diferencia entre", "ventajas y desventajas", "opinas",
            "recomienda", "estrategia", "plan", "diseña", "arquitectura",
            "resuelve", "problema", "ayúdame con", "investiga",
        ]
        
        # Si es largo o tiene triggers de profundidad → modelo grande
        if largo > 80:
            return True
        if any(trigger in t for trigger in deep_triggers):
            return True
        
        return False

    def learn_from_interaction(self, user_text: str, response: str) -> None:
        """
        Aprendizaje autónomo: extrae hechos y preferencias del usuario.
        NUNCA modifica el núcleo ético ni la constitución.
        """
        try:
            self.learning.extract_and_store(user_text, response, self.brain)
        except Exception:
            pass  # Aprendizaje es best-effort

    def get_learning_context(self) -> str:
        """Devuelve los aprendizajes como contexto para el LLM."""
        try:
            return self.learning.get_context_string()
        except Exception:
            return ""

    def get_learnings(self) -> list[dict]:
        """Devuelve todos los aprendizajes almacenados."""
        try:
            return self.learning.get_all()
        except Exception:
            return []

    def memory_stats(self) -> dict:
        """Estadísticas de memoria."""
        try:
            conversations = self.memory.episode_count()
        except Exception:
            conversations = 0
        try:
            learnings = self.learning.count()
        except Exception:
            learnings = 0
        return {
            "conversations": conversations,
            "learnings": learnings,
            "history_turns": len(self.history) // 2,
        }

    def _trim_history(self) -> None:
        """Mantiene la memoria de trabajo dentro del límite (purga lo más viejo)."""
        max_msgs = MAX_HISTORY_TURNS * 2
        if len(self.history) > max_msgs:
            self.history = self.history[-max_msgs:]


def _build_system_prompt(constitution: Constitution, personality: Personality, emotions: EmotionalEngine) -> str:
    # Estado emocional (compacto)
    try:
        emotional_ctx = emotions.get_emotional_context()
    except Exception:
        emotional_ctx = ""
    
    # System prompt lo más corto posible para velocidad
    return (
        f"{personality.system_prompt_fragment()}\n"
        f"{emotional_ctx}\n"
    )
