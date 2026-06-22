"""
Orquestador — une todas las capas y aplica el flujo de seguridad.

Pipeline (inspirado en F.R.I.D.A.Y.):
  entrada -> personalidad/contexto -> cerebro propone -> AUDITOR revisa
          -> (si OK) ejecutor actúa / responde -> memoria registra
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..brain.llm import Brain
from ..memory.store import Memory
from .auditor import Auditor, Risk
from .config import Config, load_config
from .constitution import Constitution, load_constitution
from .personality import Personality


# Palabras que sugieren tarea de programación -> usar el modelo "coder"
CODING_HINTS = (
    "código", "codigo", "programa", "función", "funcion", "script", "python",
    "javascript", "java", "html", "css", "bug", "error en el código", "compilar",
)

MAX_HISTORY_TURNS = 12  # límite de memoria de trabajo (volátil)


@dataclass
class Astra:
    config: Config
    constitution: Constitution
    personality: Personality
    auditor: Auditor
    memory: Memory
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

        system_prompt = _build_system_prompt(constitution, personality)
        brain = Brain.from_app_config(config, system_prompt=system_prompt)

        return cls(
            config=config,
            constitution=constitution,
            personality=personality,
            auditor=auditor,
            memory=memory,
            brain=brain,
        )

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
        }

    def handle(self, user_text: str) -> str:
        """Procesa una entrada de texto pasando por el auditor y manteniendo el hilo."""
        verdict = self.auditor.review_action(user_text)
        if verdict.risk == Risk.BLOCK:
            return f"🚫 No puedo hacer eso. {verdict.reason}"
        if verdict.risk == Risk.CONFIRM:
            # Guardamos la acción pendiente para confirmar en el siguiente turno
            self.memory.remember("accion_pendiente", user_text)
            return f"⚠️ {verdict.reason} ¿Confirmas que proceda? (sí/no)"

        coding = any(h in user_text.lower() for h in CODING_HINTS)

        # Hilo de conversación (memoria de trabajo, volátil)
        self.history.append({"role": "user", "content": user_text})
        response = self.brain.chat(self.history, coding=coding)
        self.history.append({"role": "assistant", "content": response})
        self._trim_history()

        # Memoria episódica (persistente, en el perfil)
        self.memory.log_episode("conversacion", user_text)
        return self.personality.flag_figurative(response)

    def _trim_history(self) -> None:
        """Mantiene la memoria de trabajo dentro del límite (purga lo más viejo)."""
        max_msgs = MAX_HISTORY_TURNS * 2
        if len(self.history) > max_msgs:
            self.history = self.history[-max_msgs:]


def _build_system_prompt(constitution: Constitution, personality: Personality) -> str:
    return (
        "### CONSTITUCIÓN (inviolable)\n"
        f"{constitution.text}\n\n"
        "### PERSONALIDAD\n"
        f"{personality.system_prompt_fragment()}\n"
    )
