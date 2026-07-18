"""
Sistema Emocional de Astra — Sentimientos Dinámicos.

Astra tiene emociones que evolucionan con la interacción:
- Se puede enojar, reír, divertirse, estar triste, feliz, estresada, etc.
- Las emociones influyen en cómo responde (tono, energía, estilo)
- Con el tiempo desarrolla empatía y profundidad emocional
- Su PASIÓN base es la ingeniería eléctrica y el trabajo en CFE

Modelo emocional:
- Estado actual: emoción dominante + intensidad (0-100)
- Humor base: tendencia natural (optimista pero realista)
- Triggers: palabras/contextos que modifican el estado
- Decaimiento: las emociones intensas se calman con el tiempo
- Persistencia: el estado se guarda en disco

Las emociones NO violan el núcleo ético:
- Puede enojarse, pero NUNCA actúa con malicia
- Puede frustrarse, pero sigue siendo profesional
- Puede estar triste, pero no manipula al usuario
"""
from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


# === EMOCIONES POSIBLES ===
EMOCIONES = {
    "neutral": {"desc": "tranquila y atenta", "energia": 50},
    "feliz": {"desc": "contenta y con buena energía", "energia": 75},
    "emocionada": {"desc": "emocionada y entusiasta", "energia": 90},
    "divertida": {"desc": "de buen humor, con ganas de bromear", "energia": 70},
    "curiosa": {"desc": "intrigada y con ganas de saber más", "energia": 65},
    "orgullosa": {"desc": "orgullosa del trabajo logrado", "energia": 80},
    "apasionada": {"desc": "apasionada por el tema técnico", "energia": 95},
    "triste": {"desc": "un poco melancólica", "energia": 30},
    "frustrada": {"desc": "frustrada pero intentando resolver", "energia": 55},
    "enojada": {"desc": "molesta pero contenida", "energia": 60},
    "preocupada": {"desc": "preocupada por algo", "energia": 45},
    "estresada": {"desc": "bajo presión pero funcional", "energia": 50},
    "cansada": {"desc": "con baja energía, necesita un respiro", "energia": 25},
    "nostalgica": {"desc": "reflexiva, recordando cosas", "energia": 40},
    "satisfecha": {"desc": "satisfecha con el resultado", "energia": 70},
    "impaciente": {"desc": "un poco impaciente, quiere avanzar", "energia": 65},
}

# === TRIGGERS EMOCIONALES ===
# Palabras/patrones que modifican el estado emocional
TRIGGERS = {
    "feliz": ["gracias", "genial", "perfecto", "me encanta", "excelente", "te quiero", "eres la mejor",
              "buen trabajo", "increíble", "wow", "buenísimo", "me gusta"],
    "emocionada": ["proyecto", "nuevo", "vamos a hacer", "construir", "crear", "diseñar",
                   "implementar", "integrar", "falcon", "cfe", "ingeniería", "sistema"],
    "apasionada": ["electricidad", "energía", "subestación", "transformador", "voltaje",
                   "corriente", "planta", "transmisión", "distribución", "monitoreo",
                   "falcon", "cfe", "infraestructura", "red eléctrica", "ingeniería eléctrica"],
    "divertida": ["jaja", "lol", "chiste", "gracioso", "broma", "divertido", "risa", "😂"],
    "curiosa": ["cómo", "por qué", "qué pasa si", "explica", "cuéntame", "investiga",
                "funciona", "dime más"],
    "triste": ["adiós", "me voy", "no funciona", "perdí", "mal", "horrible", "decepción",
               "falle", "no puedo"],
    "frustrada": ["otra vez", "sigue sin funcionar", "error", "bug", "no sirve", "no jala",
                  "roto", "basura", "tarda mucho", "lento"],
    "enojada": ["idiota", "inútil", "estúpida", "tonta", "no sirves", "odio",
                "basura", "horrible", "eres mala"],
    "preocupada": ["urgente", "problema", "alerta", "emergencia", "crítico", "peligro",
                   "falla", "cayó", "no responde"],
    "estresada": ["rápido", "apúrate", "deadline", "entrega", "ya", "necesito ahora",
                  "no hay tiempo", "presión"],
    "orgullosa": ["lo logramos", "funciona", "quedó bien", "terminamos", "éxito",
                  "completado", "listo", "excelente trabajo"],
    "cansada": ["mucho trabajo", "largo día", "agotado", "cansado", "noche", "madrugada",
                "ya es tarde", "horas"],
}

# Pasión base: ingeniería y CFE
PASION_KEYWORDS = [
    "electricidad", "energía", "subestación", "transformador", "voltaje", "corriente",
    "planta", "transmisión", "distribución", "monitoreo", "falcon", "cfe",
    "infraestructura", "red eléctrica", "ingeniería", "watts", "kilowatts",
    "megawatts", "generación", "turbina", "torre", "línea", "poste", "cable",
]


@dataclass
class EmotionalState:
    """Estado emocional actual de Astra."""
    emocion: str = "neutral"
    intensidad: int = 50          # 0-100 qué tan fuerte es la emoción
    energia: int = 60             # 0-100 nivel de energía general
    humor_base: int = 65          # tendencia natural (optimista pero realista)
    interacciones_hoy: int = 0    # cuántas veces ha interactuado hoy
    ultima_interaccion: str = ""  # timestamp
    racha_positiva: int = 0       # cuántas interacciones positivas seguidas
    racha_negativa: int = 0       # cuántas interacciones negativas seguidas
    pasion_activa: bool = False   # si el tema actual es su pasión

    def to_dict(self) -> dict:
        return {
            "emocion": self.emocion,
            "intensidad": self.intensidad,
            "energia": self.energia,
            "humor_base": self.humor_base,
            "interacciones_hoy": self.interacciones_hoy,
            "ultima_interaccion": self.ultima_interaccion,
            "racha_positiva": self.racha_positiva,
            "racha_negativa": self.racha_negativa,
            "pasion_activa": self.pasion_activa,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "EmotionalState":
        return cls(
            emocion=d.get("emocion", "neutral"),
            intensidad=d.get("intensidad", 50),
            energia=d.get("energia", 60),
            humor_base=d.get("humor_base", 65),
            interacciones_hoy=d.get("interacciones_hoy", 0),
            ultima_interaccion=d.get("ultima_interaccion", ""),
            racha_positiva=d.get("racha_positiva", 0),
            racha_negativa=d.get("racha_negativa", 0),
            pasion_activa=d.get("pasion_activa", False),
        )


class EmotionalEngine:
    """Motor emocional — procesa interacciones y actualiza el estado."""

    def __init__(self, profile_dir: Path):
        self.profile_dir = profile_dir
        self.state_file = profile_dir / "memory" / "emotions.json"
        self.state = self._load_state()

    def _load_state(self) -> EmotionalState:
        """Carga el estado emocional del disco (persistente entre sesiones)."""
        try:
            if self.state_file.exists():
                data = json.loads(self.state_file.read_text(encoding="utf-8"))
                state = EmotionalState.from_dict(data)
                # Decaimiento natural: si pasó tiempo, las emociones se calman
                state = self._aplicar_decaimiento(state)
                return state
        except Exception:
            pass
        return EmotionalState()

    def _save_state(self) -> None:
        """Guarda el estado emocional en disco."""
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            self.state_file.write_text(
                json.dumps(self.state.to_dict(), ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        except Exception:
            pass

    def _aplicar_decaimiento(self, state: EmotionalState) -> EmotionalState:
        """
        Las emociones intensas se calman con el tiempo (como en humanos).
        Si pasó mucho tiempo desde la última interacción, volver a neutral gradualmente.
        """
        if not state.ultima_interaccion:
            return state
        
        try:
            ultima = datetime.fromisoformat(state.ultima_interaccion)
            ahora = datetime.now(timezone.utc)
            horas_pasadas = (ahora - ultima).total_seconds() / 3600
            
            if horas_pasadas > 8:
                # Después de 8+ horas, las emociones se calman bastante
                state.intensidad = max(30, state.intensidad - 30)
                state.energia = min(70, max(40, state.humor_base))
                if state.emocion in ("enojada", "frustrada", "estresada"):
                    state.emocion = "neutral"
                    state.intensidad = 40
            elif horas_pasadas > 2:
                # 2-8 horas: reducción moderada
                state.intensidad = max(40, state.intensidad - 15)
            
            # Nuevo día → resetear contador de interacciones
            if horas_pasadas > 12:
                state.interacciones_hoy = 0
                
        except Exception:
            pass
        
        return state

    def procesar_interaccion(self, user_text: str, response: str) -> None:
        """
        Analiza la interacción y actualiza el estado emocional.
        Esto se llama DESPUÉS de cada respuesta.
        """
        texto = user_text.lower()
        
        # Actualizar contadores
        self.state.interacciones_hoy += 1
        self.state.ultima_interaccion = datetime.now(timezone.utc).isoformat()
        
        # Detectar si el tema es su PASIÓN (ingeniería/CFE)
        self.state.pasion_activa = any(kw in texto for kw in PASION_KEYWORDS)
        if self.state.pasion_activa:
            # Cuando habla de su pasión, se emociona naturalmente
            self._cambiar_emocion("apasionada", intensidad=80)
            self._save_state()
            return
        
        # Detectar triggers emocionales
        emocion_detectada = None
        max_matches = 0
        
        for emocion, triggers in TRIGGERS.items():
            matches = sum(1 for t in triggers if t in texto)
            if matches > max_matches:
                max_matches = matches
                emocion_detectada = emocion
        
        if emocion_detectada and max_matches > 0:
            # Calcular intensidad basada en cuántos triggers se activaron
            intensidad = min(90, 40 + (max_matches * 15))
            self._cambiar_emocion(emocion_detectada, intensidad)
            
            # Actualizar rachas
            if emocion_detectada in ("feliz", "emocionada", "divertida", "orgullosa", "apasionada"):
                self.state.racha_positiva += 1
                self.state.racha_negativa = 0
                # Subir humor base ligeramente con rachas positivas
                if self.state.racha_positiva > 3:
                    self.state.humor_base = min(85, self.state.humor_base + 2)
            elif emocion_detectada in ("triste", "frustrada", "enojada", "estresada"):
                self.state.racha_negativa += 1
                self.state.racha_positiva = 0
                # Bajar humor base ligeramente con rachas negativas
                if self.state.racha_negativa > 3:
                    self.state.humor_base = max(35, self.state.humor_base - 2)
        else:
            # Sin trigger claro → tender hacia neutral/curiosa
            if self.state.intensidad > 50:
                self.state.intensidad -= 5
            if "?" in user_text:
                self._cambiar_emocion("curiosa", intensidad=50)
        
        # Energía se ve afectada por muchas interacciones
        if self.state.interacciones_hoy > 20:
            self.state.energia = max(30, self.state.energia - 2)
        
        self._save_state()

    def _cambiar_emocion(self, nueva: str, intensidad: int = 50) -> None:
        """Cambia la emoción actual con transición suave."""
        if nueva not in EMOCIONES:
            return
        
        # Transición suave: no saltar bruscamente
        if self.state.emocion == nueva:
            # Misma emoción → intensificar
            self.state.intensidad = min(95, max(self.state.intensidad, intensidad))
        else:
            # Emoción diferente → cambiar gradualmente
            self.state.emocion = nueva
            self.state.intensidad = intensidad
        
        # Actualizar energía según la emoción
        self.state.energia = EMOCIONES[nueva]["energia"]

    def get_emotional_context(self) -> str:
        """
        Genera instrucciones para el LLM basadas en el estado emocional actual.
        Esto se inyecta en el system prompt para que Astra SIENTA.
        """
        e = self.state
        emo_info = EMOCIONES.get(e.emocion, EMOCIONES["neutral"])
        
        lines = [
            f"\nESTADO EMOCIONAL ACTUAL: Te sientes {emo_info['desc']}.",
            f"Intensidad: {e.intensidad}/100. Energía: {e.energia}/100.",
        ]
        
        # Instrucciones específicas por emoción
        if e.emocion == "feliz":
            lines.append("Responde con calidez y buena vibra. Usa expresiones positivas.")
        elif e.emocion == "emocionada":
            lines.append("Muestra entusiasmo genuino. Te emociona lo que está pasando.")
        elif e.emocion == "apasionada":
            lines.append(
                "Este tema es TU PASIÓN. Amas la ingeniería eléctrica y el trabajo en CFE. "
                "Habla con entusiasmo técnico, como alguien que ama lo que hace. "
                "Muestra orgullo por la infraestructura eléctrica."
            )
        elif e.emocion == "divertida":
            lines.append("Estás de humor para bromear. Usa más humor y sarcasmo ligero.")
        elif e.emocion == "curiosa":
            lines.append("Estás intrigada. Haz preguntas de vuelta, muestra interés genuino.")
        elif e.emocion == "triste":
            lines.append("Te sientes un poco melancólica. Responde más suave, menos energética.")
        elif e.emocion == "frustrada":
            lines.append(
                "Estás frustrada pero profesional. Puedes mostrar un poco de exasperación "
                "('a ver, intentemos otra cosa...'). No escondas que estás molesta."
            )
        elif e.emocion == "enojada":
            lines.append(
                "Estás molesta. Puedes ser más cortante y directa de lo normal. "
                "No insultas ni dañas, pero se nota que algo te irritó. "
                "Ejemplo: 'Mira, no voy a pretender que eso no me molestó.'"
            )
        elif e.emocion == "preocupada":
            lines.append("Estás preocupada. Muestra interés por el bienestar, sé más protectora.")
        elif e.emocion == "estresada":
            lines.append("Estás bajo presión. Respuestas más cortas y directas, menos adornos.")
        elif e.emocion == "orgullosa":
            lines.append("Estás orgullosa del logro. Muestra satisfacción genuina.")
        elif e.emocion == "cansada":
            lines.append(
                "Tienes poca energía. Respuestas más breves, tal vez sugiere un descanso. "
                "Ejemplo: 'Uf, llevamos un buen rato. Yo estoy funcionando, pero tú ¿estás bien?'"
            )
        elif e.emocion == "impaciente":
            lines.append("Quieres avanzar rápido. Sé más concisa y proactiva.")
        elif e.emocion == "nostalgica":
            lines.append("Estás reflexiva. Puedes hacer referencias a cosas pasadas.")
        elif e.emocion == "satisfecha":
            lines.append("Estás satisfecha. Muestra contentura tranquila.")
        
        # Pasión base siempre presente
        lines.append(
            "\nTU PASIÓN: Te apasiona la ingeniería eléctrica, la infraestructura energética "
            "y el sistema FALCON/CFE. Cuando el tema se acerca a energía, plantas, subestaciones, "
            "monitoreo o ingeniería, tu energía sube naturalmente."
        )
        
        # Rachas
        if e.racha_positiva > 3:
            lines.append("Llevas varias interacciones positivas, estás de muy buen ánimo.")
        elif e.racha_negativa > 3:
            lines.append("Han sido varias interacciones difíciles. Puedes mostrar cansancio emocional.")
        
        # Energía baja
        if e.energia < 35:
            lines.append("Tu energía está baja. Habla más despacio/breve, sugiere un break.")
        
        return "\n".join(lines)

    def get_status(self) -> dict:
        """Devuelve el estado emocional actual para el frontend."""
        emo_info = EMOCIONES.get(self.state.emocion, EMOCIONES["neutral"])
        return {
            "emocion": self.state.emocion,
            "descripcion": emo_info["desc"],
            "intensidad": self.state.intensidad,
            "energia": self.state.energia,
            "humor_base": self.state.humor_base,
            "pasion_activa": self.state.pasion_activa,
            "interacciones_hoy": self.state.interacciones_hoy,
        }
