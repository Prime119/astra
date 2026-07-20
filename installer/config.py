"""
ASTRA Installer — Configuración central de modelos y rutas.

Registro completo de modelos soportados con sus metadatos,
URLs de descarga (HuggingFace), tamaños y requisitos de hardware.
"""
from __future__ import annotations

import os
from pathlib import Path
from dataclasses import dataclass, field


# === RUTAS DEL SISTEMA ===
ASTRA_ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = ASTRA_ROOT / "models"
LLAMA_CPP_DIR = ASTRA_ROOT / "llama-cpp"
CONFIG_DIR = ASTRA_ROOT / "config"
INSTALLER_STATE_FILE = CONFIG_DIR / ".installer_state.json"

# Crear directorio de modelos si no existe
MODELS_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class ModelInfo:
    """Información completa de un modelo GGUF."""
    id: str                          # Identificador único
    name: str                        # Nombre para mostrar al usuario
    description: str                 # Descripción breve
    filename: str                    # Nombre del archivo .gguf
    size_mb: int                     # Tamaño en MB
    ram_required_gb: float           # RAM mínima requerida
    download_url: str                # URL directa de HuggingFace
    category: str                    # conversacion | codigo | vision | base
    speed: str                       # rapido | medio | lento
    quality: str                     # basica | buena | excelente
    context_length: int = 2048       # Ventana de contexto por defecto
    recommended_for: list[str] = field(default_factory=list)  # Tipos de tarea
    requires_gpu: bool = False       # Si necesita GPU
    supports_vision: bool = False    # Si soporta imágenes


# === REGISTRO DE MODELOS ===
MODELS_REGISTRY: dict[str, ModelInfo] = {
    "qwen2.5-1.5b-instruct": ModelInfo(
        id="qwen2.5-1.5b-instruct",
        name="Qwen 2.5 1.5B Instruct",
        description="Modelo ligero y rápido para conversación casual",
        filename="qwen2.5-1.5b-instruct-q4_k_m.gguf",
        size_mb=986,
        ram_required_gb=2.0,
        download_url="https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf",
        category="conversacion",
        speed="rapido",
        quality="basica",
        context_length=2048,
        recommended_for=["saludos", "preguntas_simples", "chat_casual", "comandos"],
    ),
    "qwen2.5-3b-instruct": ModelInfo(
        id="qwen2.5-3b-instruct",
        name="Qwen 2.5 3B Instruct",
        description="Conversación profunda con mejor razonamiento",
        filename="qwen2.5-3b-instruct-q4_k_m.gguf",
        size_mb=1900,
        ram_required_gb=3.5,
        download_url="https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF/resolve/main/qwen2.5-3b-instruct-q4_k_m.gguf",
        category="conversacion",
        speed="medio",
        quality="buena",
        context_length=4096,
        recommended_for=["preguntas_complejas", "explicaciones", "razonamiento", "analisis"],
    ),
    "qwen2.5-coder-3b": ModelInfo(
        id="qwen2.5-coder-3b",
        name="Qwen 2.5 Coder 3B",
        description="Especializado en generación y análisis de código",
        filename="qwen2.5-coder-3b-instruct-q4_k_m.gguf",
        size_mb=1900,
        ram_required_gb=3.5,
        download_url="https://huggingface.co/Qwen/Qwen2.5-Coder-3B-Instruct-GGUF/resolve/main/qwen2.5-coder-3b-instruct-q4_k_m.gguf",
        category="codigo",
        speed="medio",
        quality="excelente",
        context_length=4096,
        recommended_for=["codigo", "programacion", "debug", "scripts", "explicar_codigo"],
    ),
    "qwen2.5-3b": ModelInfo(
        id="qwen2.5-3b",
        name="Qwen 2.5 3B Base",
        description="Modelo base general para diversas tareas",
        filename="qwen2.5-3b-instruct-q4_k_m.gguf",
        size_mb=1900,
        ram_required_gb=3.5,
        download_url="https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF/resolve/main/qwen2.5-3b-instruct-q4_k_m.gguf",
        category="base",
        speed="medio",
        quality="buena",
        context_length=4096,
        recommended_for=["general", "resumen", "traduccion", "creatividad"],
    ),
    "astra-qwen2.5-3b": ModelInfo(
        id="astra-qwen2.5-3b",
        name="Astra Custom (Qwen 3B fine-tuned)",
        description="Modelo personalizado de Astra con fine-tuning propio",
        filename="astra-qwen2.5-3b.gguf",
        size_mb=1900,
        ram_required_gb=3.5,
        download_url="",  # Se generará con fine-tuning local
        category="conversacion",
        speed="medio",
        quality="excelente",
        context_length=4096,
        recommended_for=["personalidad", "memoria", "contexto_personal"],
    ),
    "llava-v1.5-7b": ModelInfo(
        id="llava-v1.5-7b",
        name="LLaVA 1.5 7B (Visión)",
        description="Modelo multimodal — puede ver y describir imágenes",
        filename="llava-v1.5-7b-q4_k_m.gguf",
        size_mb=4700,
        ram_required_gb=6.0,
        download_url="https://huggingface.co/mys/ggml_llava-v1.5-7b/resolve/main/ggml-model-q4_k.gguf",
        category="vision",
        speed="lento",
        quality="excelente",
        context_length=2048,
        recommended_for=["imagenes", "vision", "descripcion_visual", "analisis_imagen"],
        requires_gpu=False,
        supports_vision=True,
    ),
}


# === PERFILES DE HARDWARE ===
@dataclass
class HardwareProfile:
    """Perfil de recomendación basado en hardware disponible."""
    tier: str               # low | mid | high
    ram_gb: float
    has_gpu: bool
    gpu_vram_gb: float
    free_disk_gb: float
    recommended_models: list[str]
    max_concurrent_models: int


HARDWARE_TIERS = {
    "low": {  # 4-6 GB RAM, sin GPU
        "min_ram": 4.0,
        "max_ram": 6.0,
        "models": ["qwen2.5-1.5b-instruct"],
        "max_concurrent": 1,
        "description": "PC básica — solo modelo ligero",
    },
    "mid": {  # 6-12 GB RAM, sin/con GPU básica
        "min_ram": 6.0,
        "max_ram": 12.0,
        "models": ["qwen2.5-1.5b-instruct", "qwen2.5-3b-instruct", "qwen2.5-coder-3b"],
        "max_concurrent": 1,
        "description": "PC media — modelos de 3B funcionan bien",
    },
    "high": {  # 12+ GB RAM, GPU dedicada
        "min_ram": 12.0,
        "max_ram": 999.0,
        "models": ["qwen2.5-1.5b-instruct", "qwen2.5-3b-instruct", "qwen2.5-coder-3b", "llava-v1.5-7b"],
        "max_concurrent": 2,
        "description": "PC potente — todos los modelos disponibles",
    },
}


# === CONFIGURACIÓN DEL SERVIDOR LLAMA.CPP ===
LLAMA_SERVER_CONFIG = {
    "executable": "llama-server.exe" if os.name == "nt" else "llama-server",
    "default_port": 8080,
    "default_context": 2048,
    "default_threads": 4,  # Se ajusta automáticamente al hardware
    "default_batch_size": 512,
    "gpu_layers": 0,  # 0 = solo CPU, >0 = offload a GPU
}


# === CONFIGURACIÓN DEL INSTALADOR ===
INSTALLER_CONFIG = {
    "name": "Astra",
    "version": "1.0.0",
    "publisher": "Prime119",
    "python_embedded_version": "3.11.9",  # Python embebido (estable, compatible)
    "python_embedded_url": "https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip",
    "electron_version": "latest",
    "estimated_installer_size_mb": 300,
    "estimated_full_size_mb": 500,  # Con modelo más pequeño
}


def get_model_path(model_id: str) -> Path:
    """Devuelve la ruta completa del archivo GGUF de un modelo."""
    model = MODELS_REGISTRY.get(model_id)
    if model:
        return MODELS_DIR / model.filename
    return MODELS_DIR / f"{model_id}.gguf"


def get_installed_models() -> list[str]:
    """Lista los modelos que ya están descargados."""
    installed = []
    for model_id, model_info in MODELS_REGISTRY.items():
        model_path = MODELS_DIR / model_info.filename
        if model_path.exists():
            # Verificar que el archivo no esté corrupto (tamaño razonable)
            size_mb = model_path.stat().st_size / (1024 * 1024)
            if size_mb > 10:  # Al menos 10MB para ser un modelo válido
                installed.append(model_id)
    return installed


def get_total_download_size(model_ids: list[str]) -> int:
    """Calcula el tamaño total de descarga en MB para una lista de modelos."""
    total = 0
    for model_id in model_ids:
        model = MODELS_REGISTRY.get(model_id)
        if model and model.download_url:
            total += model.size_mb
    return total
