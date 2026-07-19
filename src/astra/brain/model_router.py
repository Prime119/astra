"""
ASTRA — Router Inteligente de Modelos.

Auto-selecciona qué modelo usar según el tipo de tarea:
- Saludos/comandos simples → modelo rápido (1.5B)
- Preguntas complejas/análisis → modelo profundo (3B instruct)
- Código/programación → modelo coder (3B coder)
- Imágenes/visión → modelo multimodal (LLaVA)

El router analiza el input del usuario y decide en <1ms qué modelo
es el más adecuado, luego le indica al ModelManager que haga switch
si es necesario.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path



# === CATEGORÍAS DE TAREA ===
class TaskType:
    """Tipos de tarea que Astra puede manejar."""
    QUICK = "quick"           # Saludos, comandos, respuestas cortas
    DEEP = "deep"             # Razonamiento, análisis, explicaciones
    CODE = "code"             # Programación, código, scripts
    VISION = "vision"         # Análisis de imágenes
    CREATIVE = "creative"     # Escritura creativa, historias
    GENERAL = "general"       # Todo lo demás


# === MAPEO TAREA → MODELO PREFERIDO ===
TASK_MODEL_MAP = {
    TaskType.QUICK: ["qwen2.5-1.5b-instruct"],
    TaskType.DEEP: ["qwen2.5-3b-instruct", "astra-qwen2.5-3b", "qwen2.5-3b"],
    TaskType.CODE: ["qwen2.5-coder-3b", "qwen2.5-3b-instruct"],
    TaskType.VISION: ["llava-v1.5-7b"],
    TaskType.CREATIVE: ["qwen2.5-3b-instruct", "astra-qwen2.5-3b"],
    TaskType.GENERAL: ["qwen2.5-3b-instruct", "qwen2.5-1.5b-instruct"],
}


# === PATRONES DE DETECCIÓN ===
# Patrones que indican tarea RÁPIDA (respuesta corta, sin pensar mucho)
QUICK_PATTERNS = [
    r"^(hola|hey|buenos? (días|tardes|noches)|qué tal|hi|hello)\b",
    r"^(gracias|ok|vale|entendido|perfecto|listo|genial|bien|bueno)\b",
    r"^(adiós|chao|bye|hasta luego|nos vemos)\b",
    r"^(sí|no|claro|obvio|dale|ya)\b",
    r"^(qué hora|qué día|qué fecha)",
    r"^(abre|abrir|ejecuta|cierra|pon|reproduce)\s",
    r"^(recuérdame|recuerdame|notifícame)\s",
    r"^(cómo te llamas|quién eres|qué eres)",
]

# Patrones que indican tarea de CÓDIGO
CODE_PATTERNS = [
    r"\b(código|codigo|code|script|programa|función|funcion|function)\b",
    r"\b(python|javascript|java|c\+\+|rust|html|css|sql|bash|typescript)\b",
    r"\b(variable|array|lista|diccionario|clase|objeto|método|metodo)\b",
    r"\b(bug|error|debug|debuggear|compilar|ejecutar código)\b",
    r"\b(import|def |class |function |const |let |var )\b",
    r"\b(api|endpoint|servidor|backend|frontend|framework)\b",
    r"\b(git|commit|push|pull|branch|merge|repo)\b",
    r"\b(loop|for|while|if|else|try|catch|except)\b",
    r"```",  # Bloques de código
    r"\b(algorit|estructura de datos|complejidad|recursión|recursion)\b",
    r"\b(crea un script|escribe un programa|haz un código|genera código)\b",
]

# Patrones que indican tarea PROFUNDA (requiere razonamiento)
DEEP_PATTERNS = [
    r"\b(explica|explícame|explicame|cómo funciona|por qué|porque)\b",
    r"\b(analiza|analizar|análisis|compara|comparación|diferencia)\b",
    r"\b(ventajas|desventajas|pros|contras)\b",
    r"\b(resumen|resume|resumir|sintetiza)\b",
    r"\b(qué opinas|qué piensas|tu opinión|recomiendas)\b",
    r"\b(historia|filosofía|ciencia|física|matemática|biología)\b",
    r"\b(estrategia|plan|planifica|diseña|arquitectura)\b",
    r"\b(investiga|investigación|profundiza|detalle|detalles)\b",
    r"\b(enseñame|enséñame|tutorial|paso a paso)\b",
    r"\b(complejo|difícil|avanzado|profundo|detallad)\b",
]

# Patrones que indican tarea CREATIVA
CREATIVE_PATTERNS = [
    r"\b(escribe|redacta|crea|genera|inventa|imagina)\b.*\b(historia|cuento|poema|canción|carta|ensayo)\b",
    r"\b(historia|cuento|poema|canción|relato|narrativa|ficción)\b",
    r"\b(personaje|trama|diálogo|escena|capítulo)\b",
    r"\b(creativ|imaginación|fantasía|ficción)\b",
]

# Patrones que indican VISIÓN (imágenes)
VISION_PATTERNS = [
    r"\b(imagen|foto|fotografía|picture|image|captura)\b",
    r"\b(ve|mira|observa|analiza|describe)\b.*\b(imagen|foto)\b",
    r"\b(qué ves|qué hay|que se ve|identifica)\b",
    r"\b(cámara|camera|webcam|screenshot|pantalla)\b",
]



@dataclass
class RoutingDecision:
    """Resultado de una decisión de routing."""
    task_type: str
    model_id: str
    confidence: float  # 0.0 a 1.0
    reason: str
    needs_switch: bool  # Si necesita cambiar de modelo
    estimated_tokens: int  # Tokens estimados de respuesta


@dataclass
class RouterStats:
    """Estadísticas del router para optimización."""
    total_requests: int = 0
    quick_count: int = 0
    deep_count: int = 0
    code_count: int = 0
    vision_count: int = 0
    creative_count: int = 0
    general_count: int = 0
    model_switches: int = 0
    avg_decision_ms: float = 0.0
    _decision_times: list = field(default_factory=list)


class ModelRouter:
    """
    Router inteligente que decide qué modelo usar para cada tarea.
    
    Funciona en <1ms analizando el texto con regex + heurísticas.
    No usa LLM para la decisión (sería circular).
    """

    def __init__(self, installed_models: list[str] = None):
        """
        Args:
            installed_models: Lista de model_ids instalados disponibles.
                              Si None, se detectan automáticamente.
        """
        self._installed = installed_models or []
        self._current_model: str = ""
        self._stats = RouterStats()
        self._last_task_type: str = TaskType.GENERAL

        # Compilar regex para rendimiento
        self._quick_re = [re.compile(p, re.IGNORECASE) for p in QUICK_PATTERNS]
        self._code_re = [re.compile(p, re.IGNORECASE) for p in CODE_PATTERNS]
        self._deep_re = [re.compile(p, re.IGNORECASE) for p in DEEP_PATTERNS]
        self._creative_re = [re.compile(p, re.IGNORECASE) for p in CREATIVE_PATTERNS]
        self._vision_re = [re.compile(p, re.IGNORECASE) for p in VISION_PATTERNS]

    def set_installed_models(self, models: list[str]):
        """Actualiza la lista de modelos instalados."""
        self._installed = models

    def set_current_model(self, model_id: str):
        """Registra qué modelo está cargado actualmente."""
        self._current_model = model_id

    def route(self, user_input: str, has_image: bool = False) -> RoutingDecision:
        """
        Analiza el input del usuario y decide qué modelo usar.
        
        Args:
            user_input: Texto del usuario
            has_image: Si el mensaje incluye una imagen
            
        Returns:
            RoutingDecision con el modelo elegido y metadata
        """
        start_time = time.perf_counter()

        # Si hay imagen, usar modelo de visión directamente
        if has_image:
            decision = self._decide_vision(user_input)
        else:
            decision = self._analyze_and_decide(user_input)

        # Calcular tiempo de decisión
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        self._stats._decision_times.append(elapsed_ms)
        if len(self._stats._decision_times) > 100:
            self._stats._decision_times = self._stats._decision_times[-50:]
        self._stats.avg_decision_ms = sum(self._stats._decision_times) / len(self._stats._decision_times)

        # Actualizar stats
        self._stats.total_requests += 1
        stat_map = {
            TaskType.QUICK: "quick_count",
            TaskType.DEEP: "deep_count",
            TaskType.CODE: "code_count",
            TaskType.VISION: "vision_count",
            TaskType.CREATIVE: "creative_count",
            TaskType.GENERAL: "general_count",
        }
        attr = stat_map.get(decision.task_type, "general_count")
        setattr(self._stats, attr, getattr(self._stats, attr) + 1)

        if decision.needs_switch:
            self._stats.model_switches += 1

        self._last_task_type = decision.task_type
        return decision


    def _analyze_and_decide(self, text: str) -> RoutingDecision:
        """Analiza el texto y decide el tipo de tarea + modelo."""
        text_lower = text.lower().strip()
        text_len = len(text)

        # Calcular scores para cada categoría
        scores = {
            TaskType.QUICK: self._score_quick(text_lower, text_len),
            TaskType.CODE: self._score_code(text_lower, text_len),
            TaskType.DEEP: self._score_deep(text_lower, text_len),
            TaskType.CREATIVE: self._score_creative(text_lower, text_len),
            TaskType.VISION: self._score_vision(text_lower),
        }

        # Elegir la categoría con mayor score
        best_type = max(scores, key=scores.get)
        best_score = scores[best_type]

        # Si ninguno tiene score significativo, usar GENERAL
        if best_score < 0.3:
            # Heurística por longitud: textos cortos → quick, largos → deep
            if text_len < 20:
                best_type = TaskType.QUICK
                best_score = 0.5
            elif text_len > 100:
                best_type = TaskType.DEEP
                best_score = 0.4
            else:
                best_type = TaskType.GENERAL
                best_score = 0.5

        # Resolver modelo
        model_id = self._resolve_model(best_type)
        needs_switch = (model_id != self._current_model) and bool(self._current_model)

        # Estimar tokens de respuesta
        estimated_tokens = self._estimate_response_tokens(best_type, text_len)

        return RoutingDecision(
            task_type=best_type,
            model_id=model_id,
            confidence=min(1.0, best_score),
            reason=self._get_reason(best_type),
            needs_switch=needs_switch,
            estimated_tokens=estimated_tokens,
        )

    def _decide_vision(self, text: str) -> RoutingDecision:
        """Decisión para tareas de visión."""
        model_id = self._resolve_model(TaskType.VISION)
        needs_switch = (model_id != self._current_model) and bool(self._current_model)

        return RoutingDecision(
            task_type=TaskType.VISION,
            model_id=model_id,
            confidence=0.95,
            reason="Imagen detectada → modelo de visión",
            needs_switch=needs_switch,
            estimated_tokens=200,
        )

    def _score_quick(self, text: str, length: int) -> float:
        """Score para tarea rápida."""
        score = 0.0

        # Patrones directos
        matches = sum(1 for r in self._quick_re if r.search(text))
        score += matches * 0.4

        # Longitud corta favorece quick
        if length < 10:
            score += 0.5
        elif length < 25:
            score += 0.3
        elif length < 50:
            score += 0.1

        # Si no tiene signos de pregunta ni es largo, probablemente es quick
        if "?" not in text and length < 30:
            score += 0.2

        return min(1.0, score)

    def _score_code(self, text: str, length: int) -> float:
        """Score para tarea de código."""
        score = 0.0

        matches = sum(1 for r in self._code_re if r.search(text))
        score += matches * 0.25

        # Presencia de código inline
        if "`" in text or "```" in text:
            score += 0.4

        # Palabras técnicas de programación
        tech_words = ["variable", "función", "class", "import", "return",
                      "algoritmo", "compilar", "debugg", "api", "http"]
        tech_count = sum(1 for w in tech_words if w in text)
        score += tech_count * 0.15

        return min(1.0, score)

    def _score_deep(self, text: str, length: int) -> float:
        """Score para tarea profunda."""
        score = 0.0

        matches = sum(1 for r in self._deep_re if r.search(text))
        score += matches * 0.25

        # Textos largos con preguntas tienden a ser deep
        if "?" in text and length > 50:
            score += 0.2
        if length > 100:
            score += 0.15
        if length > 200:
            score += 0.1

        # Múltiples preguntas
        question_count = text.count("?")
        if question_count >= 2:
            score += 0.2

        return min(1.0, score)

    def _score_creative(self, text: str, length: int) -> float:
        """Score para tarea creativa."""
        score = 0.0

        matches = sum(1 for r in self._creative_re if r.search(text))
        score += matches * 0.35

        # Palabras creativas
        creative_words = ["historia", "cuento", "poema", "canción", "personaje",
                          "imagina", "inventa", "ficción", "narrativa"]
        creative_count = sum(1 for w in creative_words if w in text)
        score += creative_count * 0.2

        return min(1.0, score)

    def _score_vision(self, text: str) -> float:
        """Score para tarea de visión."""
        score = 0.0

        matches = sum(1 for r in self._vision_re if r.search(text))
        score += matches * 0.4

        return min(1.0, score)


    def _resolve_model(self, task_type: str) -> str:
        """
        Resuelve qué modelo usar para un tipo de tarea,
        considerando qué modelos están instalados.
        """
        preferred_models = TASK_MODEL_MAP.get(task_type, TASK_MODEL_MAP[TaskType.GENERAL])

        # Buscar el primer modelo preferido que esté instalado
        for model_id in preferred_models:
            if model_id in self._installed:
                return model_id

        # Si ninguno de los preferidos está instalado, usar cualquiera disponible
        if self._installed:
            # Preferir el modelo actualmente cargado (evitar switch innecesario)
            if self._current_model in self._installed:
                return self._current_model
            return self._installed[0]

        # Fallback absoluto
        return "qwen2.5-1.5b-instruct"

    def _estimate_response_tokens(self, task_type: str, input_length: int) -> int:
        """Estima cuántos tokens necesitará la respuesta."""
        base_tokens = {
            TaskType.QUICK: 50,
            TaskType.DEEP: 300,
            TaskType.CODE: 250,
            TaskType.VISION: 150,
            TaskType.CREATIVE: 400,
            TaskType.GENERAL: 150,
        }
        base = base_tokens.get(task_type, 150)

        # Ajustar por longitud del input (preguntas largas → respuestas largas)
        if input_length > 200:
            base = int(base * 1.5)
        elif input_length > 100:
            base = int(base * 1.2)

        return base

    def _get_reason(self, task_type: str) -> str:
        """Genera una razón legible para la decisión."""
        reasons = {
            TaskType.QUICK: "Tarea simple → modelo rápido",
            TaskType.DEEP: "Requiere razonamiento → modelo profundo",
            TaskType.CODE: "Tarea de código → modelo especializado",
            TaskType.VISION: "Imagen → modelo de visión",
            TaskType.CREATIVE: "Tarea creativa → modelo de calidad",
            TaskType.GENERAL: "Tarea general → modelo balanceado",
        }
        return reasons.get(task_type, "Modelo general")

    def should_switch_model(self, target_model: str) -> bool:
        """
        Decide si vale la pena hacer switch de modelo.
        
        Evita switches innecesarios (ej: si el modelo actual puede manejar
        la tarea aunque no sea el óptimo).
        """
        if not self._current_model:
            return True  # No hay modelo cargado

        if target_model == self._current_model:
            return False  # Ya está cargado

        # Si el modelo actual es 3B y el target es 1.5B, no cambiar
        # (el 3B puede manejar tareas simples sin problema)
        if "3b" in self._current_model and "1.5b" in target_model:
            return False

        # Si llevamos menos de 3 requests desde el último switch, no cambiar
        # (evitar flip-flop entre modelos)
        if self._stats.model_switches > 0:
            requests_since_last = self._stats.total_requests
            if requests_since_last < 3:
                return False

        return True

    def get_stats(self) -> dict:
        """Devuelve estadísticas del router."""
        total = self._stats.total_requests or 1
        return {
            "total_requests": self._stats.total_requests,
            "distribution": {
                "quick": f"{self._stats.quick_count/total*100:.0f}%",
                "deep": f"{self._stats.deep_count/total*100:.0f}%",
                "code": f"{self._stats.code_count/total*100:.0f}%",
                "vision": f"{self._stats.vision_count/total*100:.0f}%",
                "creative": f"{self._stats.creative_count/total*100:.0f}%",
                "general": f"{self._stats.general_count/total*100:.0f}%",
            },
            "model_switches": self._stats.model_switches,
            "avg_decision_ms": round(self._stats.avg_decision_ms, 3),
            "current_model": self._current_model,
        }

    def reset_stats(self):
        """Resetea las estadísticas."""
        self._stats = RouterStats()


# === EJECUCIÓN DIRECTA PARA PRUEBAS ===
if __name__ == "__main__":
    print("=" * 60)
    print("  ASTRA — Model Router (pruebas)")
    print("=" * 60)

    # Simular modelos instalados
    router = ModelRouter(installed_models=[
        "qwen2.5-1.5b-instruct",
        "qwen2.5-3b-instruct",
        "qwen2.5-coder-3b",
    ])
    router.set_current_model("qwen2.5-1.5b-instruct")

    # Pruebas
    test_inputs = [
        "hola",
        "¿cómo estás?",
        "explícame cómo funciona la gravedad en detalle",
        "escribe un script en Python que ordene una lista",
        "crea una función JavaScript para validar emails",
        "¿qué diferencia hay entre TCP y UDP?",
        "escribe un poema sobre la luna",
        "abre el explorador de archivos",
        "gracias, eso es todo",
        "analiza la complejidad algorítmica de quicksort",
    ]

    print("\n  Resultados de routing:\n")
    for text in test_inputs:
        decision = router.route(text)
        switch_icon = "🔄" if decision.needs_switch else "  "
        print(f"  {switch_icon} [{decision.task_type:8s}] → {decision.model_id}")
        print(f"       conf={decision.confidence:.2f} | {decision.reason}")
        print(f"       input: \"{text[:50]}\"")
        print()

    print(f"  📊 Stats: {router.get_stats()}")
