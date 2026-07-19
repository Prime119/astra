"""
ASTRA Installer — Detección de Hardware.

Detecta automáticamente:
- RAM total y disponible
- GPU (NVIDIA/AMD/Intel) y VRAM
- Espacio en disco
- CPU (núcleos, frecuencia)
- Tier de hardware (low/mid/high)
- Recomendaciones de modelos para ESA PC
"""
from __future__ import annotations

import os
import platform
import subprocess
import json
from dataclasses import dataclass, field
from pathlib import Path

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


@dataclass
class GPUInfo:
    """Información de la GPU detectada."""
    name: str = "No detectada"
    vram_mb: int = 0
    vram_gb: float = 0.0
    vendor: str = "none"  # nvidia | amd | intel | none
    driver_version: str = ""
    cuda_available: bool = False
    vulkan_available: bool = False


@dataclass
class DiskInfo:
    """Información del disco."""
    total_gb: float = 0.0
    free_gb: float = 0.0
    used_percent: float = 0.0
    path: str = ""


@dataclass
class CPUInfo:
    """Información del CPU."""
    name: str = "Desconocido"
    cores_physical: int = 1
    cores_logical: int = 1
    frequency_mhz: float = 0.0
    architecture: str = ""


@dataclass
class HardwareReport:
    """Reporte completo de hardware del sistema."""
    # Sistema
    os_name: str = ""
    os_version: str = ""
    os_arch: str = ""
    
    # RAM
    ram_total_gb: float = 0.0
    ram_available_gb: float = 0.0
    ram_used_percent: float = 0.0
    
    # CPU
    cpu: CPUInfo = field(default_factory=CPUInfo)
    
    # GPU
    gpu: GPUInfo = field(default_factory=GPUInfo)
    has_usable_gpu: bool = False
    
    # Disco
    disk: DiskInfo = field(default_factory=DiskInfo)
    
    # Tier calculado
    tier: str = "low"  # low | mid | high
    tier_description: str = ""
    
    # Recomendaciones
    recommended_models: list[str] = field(default_factory=list)
    max_model_size_mb: int = 0
    can_run_vision: bool = False
    optimal_threads: int = 4
    optimal_context: int = 2048
    warnings: list[str] = field(default_factory=list)


def detect_ram() -> tuple[float, float, float]:
    """Detecta RAM total, disponible y porcentaje usado."""
    if PSUTIL_AVAILABLE:
        mem = psutil.virtual_memory()
        total_gb = round(mem.total / (1024**3), 1)
        available_gb = round(mem.available / (1024**3), 1)
        used_pct = mem.percent
        return total_gb, available_gb, used_pct
    
    # Fallback para Windows sin psutil
    if os.name == "nt":
        try:
            result = subprocess.run(
                ["wmic", "OS", "get", "TotalVisibleMemorySize,FreePhysicalMemory", "/format:csv"],
                capture_output=True, text=True, timeout=10
            )
            lines = [l.strip() for l in result.stdout.strip().split("\n") if l.strip() and "," in l]
            if len(lines) >= 2:
                parts = lines[-1].split(",")
                free_kb = int(parts[1])
                total_kb = int(parts[2])
                total_gb = round(total_kb / (1024**2), 1)
                available_gb = round(free_kb / (1024**2), 1)
                used_pct = round((1 - free_kb / total_kb) * 100, 1)
                return total_gb, available_gb, used_pct
        except Exception:
            pass
    
    return 4.0, 2.0, 50.0  # Fallback conservador


def detect_gpu() -> GPUInfo:
    """Detecta la GPU disponible (NVIDIA, AMD o Intel)."""
    gpu = GPUInfo()
    
    # Intentar NVIDIA primero (nvidia-smi)
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            parts = result.stdout.strip().split(",")
            if len(parts) >= 3:
                gpu.name = parts[0].strip()
                gpu.vram_mb = int(float(parts[1].strip()))
                gpu.vram_gb = round(gpu.vram_mb / 1024, 1)
                gpu.driver_version = parts[2].strip()
                gpu.vendor = "nvidia"
                gpu.cuda_available = True
                return gpu
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    
    # Intentar con WMIC en Windows (cualquier GPU)
    if os.name == "nt":
        try:
            result = subprocess.run(
                ["wmic", "path", "win32_VideoController", "get", 
                 "Name,AdapterRAM,DriverVersion", "/format:csv"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                lines = [l.strip() for l in result.stdout.strip().split("\n") 
                         if l.strip() and "," in l and "Name" not in l]
                for line in lines:
                    parts = line.split(",")
                    if len(parts) >= 4:
                        adapter_ram = parts[1].strip()
                        driver = parts[2].strip()
                        name = parts[3].strip()
                        
                        if not name or "Microsoft" in name:
                            continue
                        
                        gpu.name = name
                        gpu.driver_version = driver
                        
                        # Calcular VRAM
                        try:
                            vram_bytes = int(adapter_ram)
                            gpu.vram_mb = vram_bytes // (1024 * 1024)
                            gpu.vram_gb = round(gpu.vram_mb / 1024, 1)
                        except (ValueError, TypeError):
                            gpu.vram_mb = 0
                        
                        # Detectar vendor
                        name_lower = name.lower()
                        if "nvidia" in name_lower or "geforce" in name_lower or "rtx" in name_lower:
                            gpu.vendor = "nvidia"
                            gpu.cuda_available = True
                        elif "amd" in name_lower or "radeon" in name_lower:
                            gpu.vendor = "amd"
                            gpu.vulkan_available = True
                        elif "intel" in name_lower:
                            gpu.vendor = "intel"
                        
                        if gpu.vram_mb > 0:
                            return gpu
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
    
    # Linux: lspci
    if os.name != "nt":
        try:
            result = subprocess.run(
                ["lspci", "-v"],
                capture_output=True, text=True, timeout=10
            )
            if "NVIDIA" in result.stdout:
                gpu.vendor = "nvidia"
                for line in result.stdout.split("\n"):
                    if "NVIDIA" in line and "VGA" in line:
                        gpu.name = line.split(":")[-1].strip()
                        break
            elif "AMD" in result.stdout or "Radeon" in result.stdout:
                gpu.vendor = "amd"
                for line in result.stdout.split("\n"):
                    if ("AMD" in line or "Radeon" in line) and "VGA" in line:
                        gpu.name = line.split(":")[-1].strip()
                        break
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
    
    return gpu


def detect_disk(target_path: str = None) -> DiskInfo:
    """Detecta espacio en disco disponible."""
    disk = DiskInfo()
    
    if target_path is None:
        target_path = "C:\\" if os.name == "nt" else "/"
    
    disk.path = target_path
    
    if PSUTIL_AVAILABLE:
        try:
            usage = psutil.disk_usage(target_path)
            disk.total_gb = round(usage.total / (1024**3), 1)
            disk.free_gb = round(usage.free / (1024**3), 1)
            disk.used_percent = usage.percent
            return disk
        except Exception:
            pass
    
    # Fallback
    if os.name == "nt":
        try:
            result = subprocess.run(
                ["wmic", "logicaldisk", "where", "DeviceID='C:'", 
                 "get", "Size,FreeSpace", "/format:csv"],
                capture_output=True, text=True, timeout=10
            )
            lines = [l.strip() for l in result.stdout.strip().split("\n") 
                     if l.strip() and "," in l and "FreeSpace" not in l]
            if lines:
                parts = lines[-1].split(",")
                if len(parts) >= 3:
                    free_bytes = int(parts[1])
                    total_bytes = int(parts[2])
                    disk.total_gb = round(total_bytes / (1024**3), 1)
                    disk.free_gb = round(free_bytes / (1024**3), 1)
                    disk.used_percent = round((1 - free_bytes / total_bytes) * 100, 1)
        except Exception:
            pass
    else:
        try:
            stat = os.statvfs(target_path)
            disk.total_gb = round((stat.f_blocks * stat.f_frsize) / (1024**3), 1)
            disk.free_gb = round((stat.f_bavail * stat.f_frsize) / (1024**3), 1)
            disk.used_percent = round((1 - stat.f_bavail / stat.f_blocks) * 100, 1)
        except Exception:
            pass
    
    return disk


def detect_cpu() -> CPUInfo:
    """Detecta información del CPU."""
    cpu = CPUInfo()
    cpu.architecture = platform.machine()
    
    if PSUTIL_AVAILABLE:
        cpu.cores_physical = psutil.cpu_count(logical=False) or 1
        cpu.cores_logical = psutil.cpu_count(logical=True) or 1
        try:
            freq = psutil.cpu_freq()
            if freq:
                cpu.frequency_mhz = freq.max or freq.current or 0.0
        except Exception:
            pass
    
    # Obtener nombre del CPU
    if os.name == "nt":
        try:
            result = subprocess.run(
                ["wmic", "cpu", "get", "Name", "/format:csv"],
                capture_output=True, text=True, timeout=10
            )
            lines = [l.strip() for l in result.stdout.strip().split("\n") 
                     if l.strip() and "," in l and "Name" not in l]
            if lines:
                cpu.name = lines[-1].split(",")[-1].strip()
        except Exception:
            cpu.name = platform.processor() or "Desconocido"
    else:
        try:
            with open("/proc/cpuinfo", "r") as f:
                for line in f:
                    if "model name" in line:
                        cpu.name = line.split(":")[1].strip()
                        break
        except Exception:
            cpu.name = platform.processor() or "Desconocido"
    
    return cpu


def calculate_tier(ram_gb: float, gpu: GPUInfo) -> tuple[str, str]:
    """Calcula el tier de hardware basado en RAM y GPU."""
    if ram_gb >= 12 and (gpu.vram_mb >= 4096 or ram_gb >= 16):
        return "high", "PC potente — todos los modelos disponibles"
    elif ram_gb >= 6:
        return "mid", "PC media — modelos de 3B funcionan bien"
    else:
        return "low", "PC básica — solo modelo ligero recomendado"


def get_recommended_models(tier: str, ram_gb: float, free_disk_gb: float, gpu: GPUInfo) -> list[str]:
    """Genera lista de modelos recomendados según el hardware."""
    from installer.config import MODELS_REGISTRY
    
    recommended = []
    
    for model_id, model_info in MODELS_REGISTRY.items():
        # Verificar RAM suficiente (modelo + OS necesita ~2GB extra)
        ram_needed = model_info.ram_required_gb + 2.0
        if ram_gb < ram_needed:
            continue
        
        # Verificar espacio en disco
        size_gb = model_info.size_mb / 1024
        if free_disk_gb < size_gb + 1.0:  # 1GB margen
            continue
        
        # Verificar si necesita GPU
        if model_info.requires_gpu and gpu.vendor == "none":
            continue
        
        # Si el modelo custom no tiene URL, solo recomendar si ya existe
        if not model_info.download_url:
            continue
        
        recommended.append(model_id)
    
    return recommended


def get_warnings(report: HardwareReport) -> list[str]:
    """Genera advertencias basadas en el hardware detectado."""
    warnings = []
    
    if report.ram_total_gb < 4.0:
        warnings.append("RAM insuficiente (<4GB). Astra podría funcionar lenta.")
    elif report.ram_total_gb < 6.0:
        warnings.append("RAM limitada. Solo se recomienda el modelo de 1.5B.")
    
    if report.disk.free_gb < 3.0:
        warnings.append("Poco espacio en disco. Se necesitan al menos 3GB libres.")
    
    if report.ram_available_gb < 2.0:
        warnings.append("Poca RAM disponible ahora. Cierra programas antes de instalar.")
    
    if not report.has_usable_gpu:
        warnings.append("Sin GPU dedicada. Los modelos funcionarán solo con CPU (más lento pero funcional).")
    
    return warnings


def calculate_optimal_settings(cpu: CPUInfo, ram_gb: float) -> tuple[int, int]:
    """Calcula threads y contexto óptimos para llama.cpp."""
    # Threads: usar cores físicos - 1 (dejar 1 para el OS)
    optimal_threads = max(1, cpu.cores_physical - 1)
    # No usar más de 8 threads (rendimiento decreciente después)
    optimal_threads = min(optimal_threads, 8)
    
    # Contexto: basado en RAM disponible
    if ram_gb >= 12:
        optimal_context = 4096
    elif ram_gb >= 8:
        optimal_context = 2048
    elif ram_gb >= 6:
        optimal_context = 1024
    else:
        optimal_context = 512
    
    return optimal_threads, optimal_context


def full_hardware_scan() -> HardwareReport:
    """Ejecuta un escaneo completo del hardware y genera el reporte."""
    report = HardwareReport()
    
    # Sistema operativo
    report.os_name = platform.system()
    report.os_version = platform.version()
    report.os_arch = platform.machine()
    
    # RAM
    report.ram_total_gb, report.ram_available_gb, report.ram_used_percent = detect_ram()
    
    # CPU
    report.cpu = detect_cpu()
    
    # GPU
    report.gpu = detect_gpu()
    report.has_usable_gpu = (report.gpu.vendor != "none" and report.gpu.vram_mb >= 2048)
    
    # Disco
    report.disk = detect_disk()
    
    # Tier
    report.tier, report.tier_description = calculate_tier(report.ram_total_gb, report.gpu)
    
    # Recomendaciones
    report.recommended_models = get_recommended_models(
        report.tier, report.ram_total_gb, report.disk.free_gb, report.gpu
    )
    
    # Tamaño máximo de modelo que puede correr
    usable_ram = report.ram_total_gb - 2.0  # 2GB para OS
    report.max_model_size_mb = int(usable_ram * 1024 * 0.7)  # 70% de RAM utilizable
    
    # Visión
    report.can_run_vision = report.ram_total_gb >= 8.0
    
    # Settings óptimos
    report.optimal_threads, report.optimal_context = calculate_optimal_settings(
        report.cpu, report.ram_total_gb
    )
    
    # Warnings
    report.warnings = get_warnings(report)
    
    return report


def hardware_report_to_dict(report: HardwareReport) -> dict:
    """Convierte el reporte a diccionario para JSON/UI."""
    return {
        "sistema": {
            "os": f"{report.os_name} {report.os_version}",
            "arquitectura": report.os_arch,
        },
        "ram": {
            "total_gb": report.ram_total_gb,
            "disponible_gb": report.ram_available_gb,
            "uso_percent": report.ram_used_percent,
        },
        "cpu": {
            "nombre": report.cpu.name,
            "nucleos_fisicos": report.cpu.cores_physical,
            "nucleos_logicos": report.cpu.cores_logical,
            "frecuencia_mhz": report.cpu.frequency_mhz,
        },
        "gpu": {
            "nombre": report.gpu.name,
            "vram_mb": report.gpu.vram_mb,
            "vram_gb": report.gpu.vram_gb,
            "vendor": report.gpu.vendor,
            "cuda": report.gpu.cuda_available,
        },
        "disco": {
            "total_gb": report.disk.total_gb,
            "libre_gb": report.disk.free_gb,
            "uso_percent": report.disk.used_percent,
        },
        "tier": report.tier,
        "tier_descripcion": report.tier_description,
        "modelos_recomendados": report.recommended_models,
        "max_modelo_mb": report.max_model_size_mb,
        "puede_vision": report.can_run_vision,
        "threads_optimos": report.optimal_threads,
        "contexto_optimo": report.optimal_context,
        "advertencias": report.warnings,
    }


# === EJECUCIÓN DIRECTA PARA PRUEBAS ===
if __name__ == "__main__":
    print("=" * 60)
    print("  ASTRA — Escaneo de Hardware")
    print("=" * 60)
    
    report = full_hardware_scan()
    info = hardware_report_to_dict(report)
    
    print(f"\n  Sistema: {info['sistema']['os']} ({info['sistema']['arquitectura']})")
    print(f"  CPU: {info['cpu']['nombre']}")
    print(f"       {info['cpu']['nucleos_fisicos']} núcleos / {info['cpu']['nucleos_logicos']} hilos")
    print(f"  RAM: {info['ram']['total_gb']} GB total / {info['ram']['disponible_gb']} GB libre")
    print(f"  GPU: {info['gpu']['nombre']}")
    if info['gpu']['vram_gb'] > 0:
        print(f"       VRAM: {info['gpu']['vram_gb']} GB ({info['gpu']['vendor']})")
    print(f"  Disco: {info['disco']['libre_gb']} GB libres de {info['disco']['total_gb']} GB")
    
    print(f"\n  Tier: {info['tier'].upper()} — {info['tier_descripcion']}")
    print(f"  Threads óptimos: {info['threads_optimos']}")
    print(f"  Contexto óptimo: {info['contexto_optimo']}")
    
    print(f"\n  Modelos recomendados:")
    for m in info['modelos_recomendados']:
        print(f"    ✅ {m}")
    
    if info['advertencias']:
        print(f"\n  ⚠️ Advertencias:")
        for w in info['advertencias']:
            print(f"    • {w}")
    
    print()
