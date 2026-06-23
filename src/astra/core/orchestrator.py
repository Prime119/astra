"""
Orquestador — une todas las capas y aplica el flujo de seguridad (Motor Dual de Caine).

Pipeline (F.R.I.D.A.Y. + Caine + Cyborg):
  entrada
   -> verificación de integridad del núcleo (Zero-Trust)
   -> Code-Switching (detecta estrés -> modo)
   -> AUDITOR revisa la ENTRADA (BLOCK/CONFIRM/SAFE)
   -> CEREBRO (Módulo A) propone respuesta
   -> AUDITOR revisa la SALIDA (Módulo B, anti-gaslighting)
   -> responde / ejecuta -> memoria registra (con peso emocional)
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..brain.llm import Brain
from ..memory.store import Memory
from .auditor import Auditor, Risk
from .config import Config, load_config
from .constitution import Constitution, load_constitution
from .personality import MODE_CONFORT, MODE_CRISIS, Personality


# Palabras que sugieren tarea de programación -> usar el modelo "coder"
CODING_HINTS = (
    "código", "codigo", "programa", "función", "funcion", "script", "python",
    "javascript", "java", "html", "css", "bug", "error en el código", "compilar",
)

CONFIRM_YES = {"sí", "si", "sip", "claro", "confirmo", "adelante", "hazlo", "procede", "ok", "dale"}
CONFIRM_NO = {"no", "nop", "cancela", "cancelar", "mejor no", "detente", "abortar", "para"}

MAX_HISTORY_TURNS = 12  # límite de memoria de trabajo (volátil)

# Peso emocional (Koko, Shuvi) por modo, para la memoria episódica
_WEIGHT_BY_MODE = {MODE_CRISIS: 0.8, MODE_CONFORT: 0.6}


@dataclass
class Astra:
    config: Config
    constitution: Constitution
    personality: Personality
    auditor: Auditor
    memory: Memory
    brain: Brain
    integrity_ok: bool = True
    pending_action: str | None = None
    history: list[dict] = field(default_factory=list)

    @classmethod
    def boot(cls, edition: str | None = None) -> "Astra":
        config = load_config(edition=edition)
        constitution = load_constitution()
        personality = Personality.from_config(
            config.get("personality", default={}),
            name=config.name,
            persona=config.persona,
            domain_focus=config.domain_focus,
        )
        personality.clamp()
        auditor = Auditor(constitution_hash=constitution.sha256)
        memory = Memory(profile_dir=config.paths.profile_dir)

        # Verificación de integridad del núcleo ético (Zero-Trust, regla 6).
        integrity_ok = cls._check_integrity(memory, constitution)

        system_prompt = _build_system_prompt(constitution, personality, config)
        brain = Brain.from_app_config(config, system_prompt=system_prompt)

        return cls(
            config=config,
            constitution=constitution,
            personality=personality,
            auditor=auditor,
            memory=memory,
            brain=brain,
            integrity_ok=integrity_ok,
        )

    @staticmethod
    def _check_integrity(memory: Memory, constitution: Constitution) -> bool:
        """Guarda el hash del núcleo en el primer arranque y lo compara en los siguientes."""
        baseline = memory.recall("constitution_hash")
        if baseline is None:
            memory.remember("constitution_hash", constitution.sha256)
            return True
        return baseline == constitution.sha256

    def status(self) -> dict:
        return {
            "name": self.config.name,
            "edition": self.config.edition,
            "edition_name": self.config.edition_name,
            "persona": self.config.persona,
            "version_constitution": self.constitution.short_hash,
            "integrity_ok": self.integrity_ok,
            "mode": "portátil" if self.config.paths.is_portable else "residente",
            "hardware": {
                "ram_gb": self.config.hardware.ram_gb,
                "gpu": self.config.hardware.has_gpu,
                "tier": self.config.hardware.tier,
            },
            "profile_dir": str(self.config.paths.profile_dir),
            "brain_local_online": self.brain.is_local_available(),
            "brain_model": self.brain.config.local_model,
            "capabilities": self.config.capabilities,
            "personality": {
                "honesty": self.personality.honesty,
                "humor": self.personality.humor,
                "warmth": self.personality.warmth,
                "proactivity": self.personality.proactivity,
            },
        }

    def handle(self, user_text: str) -> str:
        """Procesa una entrada de texto por todo el pipeline de seguridad."""
        # 0) Parálisis preventiva si el núcleo ético fue alterado (regla 6).
        if not self.integrity_ok:
            return (
                "🛑 Parálisis preventiva: detecté que mi núcleo ético fue modificado respecto a su "
                "estado validado. Por seguridad no operaré hasta restaurarlo (o re-validarlo "
                "borrando el perfil)."
            )

        text = user_text.strip()
        if not text:
            return ""

        # 1) ¿Hay una acción pendiente de confirmación? (human-in-the-loop, volátil)
        if self.pending_action:
            return self._resolve_pending(text, self.pending_action)

        # 2) Code-Switching: detecta estrés/contexto y ajusta el modo + system prompt.
        self.personality.detect_mode(text)
        self._refresh_brain_prompt()

        # 3) Auditor revisa la ENTRADA.
        verdict = self.auditor.review_action(text)
        if verdict.risk == Risk.BLOCK:
            return f"🚫 No puedo hacer eso. {verdict.reason}"
        if verdict.risk == Risk.CONFIRM:
            self.pending_action = text
            return f"⚠️ {verdict.reason} ¿Confirmas que proceda? (sí/no)"

        # 4) Cerebro (Módulo A) propone.
        coding = any(h in text.lower() for h in CODING_HINTS)
        self.history.append({"role": "user", "content": text})
        response = self.brain.chat(self.history, coding=coding)

        # 5) Auditor revisa la SALIDA (Módulo B, anti-gaslighting).
        out_verdict = self.auditor.review_output(response)
        if out_verdict.risk == Risk.BLOCK:
            response = (
                "He preferido reformular mi respuesta: la versión anterior no cumplía mi regla de "
                "transparencia. ¿Puedes darme un poco más de contexto para responderte con claridad?"
            )

        self.history.append({"role": "assistant", "content": response})
        self._trim_history()

        # 6) Memoria episódica (persistente) con peso emocional (Koko).
        weight = _WEIGHT_BY_MODE.get(self.personality.mode, 0.2)
        self.memory.log_episode("conversacion", text, emotional_weight=weight)
        return self.personality.flag_figurative(response)

    # ------------------------------------------------------------- internos
    def _resolve_pending(self, text: str, pending: str) -> str:
        """Resuelve una acción de alto impacto que quedó esperando confirmación."""
        low = text.lower()
        if low in CONFIRM_YES:
            self.pending_action = None
            # La ejecución real de acciones del sistema llega en la Fase 4 (con sandbox).
            self.memory.log_episode("accion_confirmada", pending, emotional_weight=0.5)
            return (
                f"✅ Confirmado. Procedería con: «{pending}». (La ejecución real de acciones del "
                "sistema se habilita en la Fase 4, con sandbox y permisos.)"
            )
        if low in CONFIRM_NO:
            self.pending_action = None
            return "👍 Entendido, no procedo. Acción cancelada."
        # Respuesta ambigua: la acción sigue pendiente.
        return "¿Confirmas la acción anterior? Responde 'sí' o 'no'."

    def _refresh_brain_prompt(self) -> None:
        """Reconstruye el system prompt si el modo (y por tanto el tono) cambió."""
        self.brain.system_prompt = _build_system_prompt(
            self.constitution, self.personality, self.config
        )

    def _trim_history(self) -> None:
        """Mantiene la memoria de trabajo dentro del límite (purga lo más viejo)."""
        max_msgs = MAX_HISTORY_TURNS * 2
        if len(self.history) > max_msgs:
            self.history = self.history[-max_msgs:]


def _build_system_prompt(
    constitution: Constitution, personality: Personality, config: Config
) -> str:
    enabled = [k for k, v in config.capabilities.items() if v]
    caps = ", ".join(enabled) if enabled else "(básicas)"
    return (
        "### CONSTITUCIÓN (inviolable)\n"
        f"{constitution.text}\n\n"
        f"### EDICIÓN\n{config.edition_name} (persona: {config.persona}). "
        f"Capacidades habilitadas: {caps}.\n\n"
        "### PERSONALIDAD\n"
        f"{personality.system_prompt_fragment()}\n"
    )
