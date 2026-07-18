"""
Orquestador — une todas las capas y aplica el flujo de seguridad.

Pipeline (inspirado en F.R.I.D.A.Y.):
  entrada -> personalidad/contexto -> cerebro propone -> AUDITOR revisa
          -> (si OK) ejecutor actúa / responde -> memoria registra
          -> aprendizaje extrae hechos -> evolución continua
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..brain.llm import Brain
from ..memory.store import Memory
from ..memory.learning import LearningEngine
from .auditor import Auditor, Risk
from .config import Config, load_config
from .constitution import Constitution, load_constitution
from .personality import Personality


# Palabras que sugieren tarea de programación -> usar el modelo "coder"
CODING_HINTS = (
    "código", "codigo", "programa", "función", "funcion", "script", "python",
    "javascript", "java", "html", "css", "bug", "error en el código", "compilar",
)

MAX_HISTORY_TURNS = 20  # límite de memoria de trabajo (volátil, más amplio para mejor contexto)


@dataclass
class Astra:
    config: Config
    constitution: Constitution
    personality: Personality
    auditor: Auditor
    memory: Memory
    learning: LearningEngine
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

        system_prompt = _build_system_prompt(constitution, personality)
        brain = Brain.from_app_config(config, system_prompt=system_prompt)

        # Cargar historial previo al iniciar (continuidad de conversación)
        instance = cls(
            config=config,
            constitution=constitution,
            personality=personality,
            auditor=auditor,
            memory=memory,
            learning=learning,
            brain=brain,
        )
        instance._load_recent_history()
        return instance

    def _load_recent_history(self) -> None:
        """Carga las últimas conversaciones del perfil para mantener continuidad."""
        recent = self.memory.get_recent_conversations(limit=6)
        for entry in recent:
            self.history.append({"role": "user", "content": entry["user"]})
            self.history.append({"role": "assistant", "content": entry["assistant"]})

    def status(self) -> dict:
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
            "learnings_count": self.learning.count(),
            "memory_episodes": self.memory.episode_count(),
        }

    def handle(self, user_text: str) -> str:
        """Procesa una entrada de texto pasando por el auditor y manteniendo el hilo."""
        verdict = self.auditor.review_action(user_text)
        if verdict.risk == Risk.BLOCK:
            return f"No puedo hacer eso. {verdict.reason}"
        if verdict.risk == Risk.CONFIRM:
            self.memory.remember("accion_pendiente", user_text)
            return f"{verdict.reason} ¿Confirmas que proceda? (sí/no)"

        coding = any(h in user_text.lower() for h in CODING_HINTS)

        # Hilo de conversación (memoria de trabajo, volátil)
        self.history.append({"role": "user", "content": user_text})
        response = self.brain.chat(self.history, coding=coding)
        self.history.append({"role": "assistant", "content": response})
        self._trim_history()

        # Memoria episódica persistente
        self.memory.log_episode("conversacion", user_text)
        self.memory.save_conversation(user_text, response)
        
        return self.personality.flag_figurative(response)

    def learn_from_interaction(self, user_text: str, response: str) -> None:
        """
        Aprendizaje autónomo: extrae hechos y preferencias del usuario.
        NUNCA modifica el núcleo ético ni la constitución.
        """
        self.learning.extract_and_store(user_text, response, self.brain)

    def get_learning_context(self) -> str:
        """Devuelve los aprendizajes como contexto para el LLM."""
        return self.learning.get_context_string()

    def get_learnings(self) -> list[dict]:
        """Devuelve todos los aprendizajes almacenados."""
        return self.learning.get_all()

    def memory_stats(self) -> dict:
        """Estadísticas de memoria."""
        return {
            "conversations": self.memory.episode_count(),
            "learnings": self.learning.count(),
            "history_turns": len(self.history) // 2,
        }

    def _trim_history(self) -> None:
        """Mantiene la memoria de trabajo dentro del límite (purga lo más viejo)."""
        max_msgs = MAX_HISTORY_TURNS * 2
        if len(self.history) > max_msgs:
            self.history = self.history[-max_msgs:]


def _build_system_prompt(constitution: Constitution, personality: Personality) -> str:
    return (
        "### CONSTITUCIÓN (inviolable — NUNCA puedes violar ni modificar estas reglas)\n"
        f"{constitution.text}\n\n"
        "### PERSONALIDAD\n"
        f"{personality.system_prompt_fragment()}\n"
    )
