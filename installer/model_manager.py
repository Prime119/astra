"""
ASTRA Installer — Gestor de Modelos.

Descarga, verifica e instala modelos GGUF desde HuggingFace.
Características:
- Descarga con barra de progreso y reanudación
- Verificación de integridad (tamaño + hash parcial)
- Gestión del ciclo de vida (instalar, desinstalar, listar)
- Lanzamiento de llama-server con el modelo correcto
- Hot-swap de modelos sin reiniciar el servidor
"""
from __future__ import annotations

import os
import sys
import json
import time
import hashlib
import subprocess
import threading
from pathlib import Path
from dataclasses import dataclass, field
from typing import Callable, Optional

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

from installer.config import (
    MODELS_REGISTRY, MODELS_DIR, LLAMA_CPP_DIR,
    LLAMA_SERVER_CONFIG, INSTALLER_STATE_FILE, CONFIG_DIR,
    ModelInfo, get_model_path, get_installed_models,
)


# === TIPOS DE CALLBACK ===
ProgressCallback = Callable[[str, float, str], None]
# (model_id, progress_0_to_1, status_message)


@dataclass
class DownloadState:
    """Estado de una descarga en progreso."""
    model_id: str
    total_bytes: int = 0
    downloaded_bytes: int = 0
    speed_mbps: float = 0.0
    eta_seconds: float = 0.0
    status: str = "pendiente"  # pendiente | descargando | verificando | completo | error
    error_message: str = ""
    
    @property
    def progress(self) -> float:
        if self.total_bytes == 0:
            return 0.0
        return min(1.0, self.downloaded_bytes / self.total_bytes)
    
    @property
    def downloaded_mb(self) -> float:
        return self.downloaded_bytes / (1024 * 1024)
    
    @property
    def total_mb(self) -> float:
        return self.total_bytes / (1024 * 1024)


@dataclass 
class ServerState:
    """Estado del servidor llama.cpp."""
    running: bool = False
    pid: int = 0
    process: Optional[subprocess.Popen] = None
    current_model: str = ""
    port: int = 8080
    threads: int = 4
    context_length: int = 2048


class ModelManager:
    """Gestor principal de modelos GGUF para Astra."""
    
    def __init__(self, models_dir: Path = None, llama_dir: Path = None):
        self.models_dir = models_dir or MODELS_DIR
        self.llama_dir = llama_dir or LLAMA_CPP_DIR
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        self._server = ServerState()
        self._downloads: dict[str, DownloadState] = {}
        self._download_lock = threading.Lock()
        
        # Cargar estado persistente
        self._state = self._load_state()
    
    # =================================================================
    # ESTADO PERSISTENTE
    # =================================================================
    
    def _load_state(self) -> dict:
        """Carga el estado guardado del instalador."""
        try:
            if INSTALLER_STATE_FILE.exists():
                return json.loads(INSTALLER_STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
        return {
            "installed_models": [],
            "active_model": "",
            "first_run_complete": False,
            "server_config": {
                "port": 8080,
                "threads": 4,
                "context": 2048,
            }
        }
    
    def _save_state(self):
        """Guarda el estado actual."""
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            INSTALLER_STATE_FILE.write_text(
                json.dumps(self._state, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
        except Exception as e:
            print(f"⚠️ No se pudo guardar estado: {e}")
    
    # =================================================================
    # INFORMACIÓN DE MODELOS
    # =================================================================
    
    def list_available_models(self) -> list[dict]:
        """Lista todos los modelos disponibles con su estado."""
        models = []
        installed = self.get_installed_models()
        
        for model_id, info in MODELS_REGISTRY.items():
            models.append({
                "id": model_id,
                "name": info.name,
                "description": info.description,
                "size_mb": info.size_mb,
                "ram_required_gb": info.ram_required_gb,
                "category": info.category,
                "speed": info.speed,
                "quality": info.quality,
                "installed": model_id in installed,
                "has_download_url": bool(info.download_url),
                "is_active": self._server.current_model == model_id,
            })
        
        return models
    
    def get_installed_models(self) -> list[str]:
        """Lista modelos instalados verificando archivos en disco."""
        installed = []
        for model_id, info in MODELS_REGISTRY.items():
            model_path = self.models_dir / info.filename
            if model_path.exists():
                size_mb = model_path.stat().st_size / (1024 * 1024)
                # El archivo debe tener al menos 50% del tamaño esperado
                if size_mb > info.size_mb * 0.5:
                    installed.append(model_id)
        return installed
    
    def get_model_info(self, model_id: str) -> Optional[ModelInfo]:
        """Obtiene info de un modelo específico."""
        return MODELS_REGISTRY.get(model_id)
    
    def is_model_installed(self, model_id: str) -> bool:
        """Verifica si un modelo está instalado."""
        return model_id in self.get_installed_models()
    
    # =================================================================
    # DESCARGA DE MODELOS
    # =================================================================
    
    def download_model(self, model_id: str, 
                       progress_callback: ProgressCallback = None) -> bool:
        """
        Descarga un modelo de HuggingFace.
        
        Args:
            model_id: ID del modelo a descargar
            progress_callback: Función callback(model_id, progress, message)
            
        Returns:
            True si la descarga fue exitosa
        """
        if not HTTPX_AVAILABLE:
            if progress_callback:
                progress_callback(model_id, 0.0, "Error: httpx no instalado")
            return False
        
        model_info = MODELS_REGISTRY.get(model_id)
        if not model_info:
            if progress_callback:
                progress_callback(model_id, 0.0, f"Error: modelo '{model_id}' no encontrado")
            return False
        
        if not model_info.download_url:
            if progress_callback:
                progress_callback(model_id, 0.0, "Error: este modelo no tiene URL de descarga")
            return False
        
        # Preparar estado de descarga
        state = DownloadState(model_id=model_id, status="descargando")
        with self._download_lock:
            self._downloads[model_id] = state
        
        target_path = self.models_dir / model_info.filename
        temp_path = target_path.with_suffix(".gguf.part")
        
        try:
            # Verificar si ya existe una descarga parcial (para reanudar)
            resume_bytes = 0
            if temp_path.exists():
                resume_bytes = temp_path.stat().st_size
                state.downloaded_bytes = resume_bytes
            
            # Headers para reanudación
            headers = {}
            if resume_bytes > 0:
                headers["Range"] = f"bytes={resume_bytes}-"
                if progress_callback:
                    progress_callback(model_id, state.progress, 
                                     f"Reanudando descarga ({resume_bytes/(1024*1024):.0f}MB ya descargados)...")
            
            # Realizar descarga con streaming
            start_time = time.time()
            last_report_time = start_time
            
            with httpx.stream("GET", model_info.download_url, 
                            headers=headers, 
                            follow_redirects=True,
                            timeout=httpx.Timeout(connect=30.0, read=60.0, 
                                                  write=30.0, pool=30.0)) as response:
                
                # Verificar respuesta
                if response.status_code not in (200, 206):
                    state.status = "error"
                    state.error_message = f"HTTP {response.status_code}"
                    if progress_callback:
                        progress_callback(model_id, 0.0, f"Error HTTP: {response.status_code}")
                    return False
                
                # Obtener tamaño total
                content_length = int(response.headers.get("content-length", 0))
                if response.status_code == 206:
                    # Reanudación — tamaño parcial
                    state.total_bytes = resume_bytes + content_length
                else:
                    state.total_bytes = content_length
                    resume_bytes = 0  # No reanudación, empezar de cero
                    if temp_path.exists():
                        temp_path.unlink()
                
                # Escribir archivo
                mode = "ab" if resume_bytes > 0 else "wb"
                with open(temp_path, mode) as f:
                    for chunk in response.iter_bytes(chunk_size=1024 * 1024):  # 1MB chunks
                        f.write(chunk)
                        state.downloaded_bytes += len(chunk)
                        
                        # Calcular velocidad y ETA
                        elapsed = time.time() - start_time
                        if elapsed > 0:
                            speed_bytes = (state.downloaded_bytes - resume_bytes) / elapsed
                            state.speed_mbps = round(speed_bytes / (1024 * 1024), 2)
                            remaining_bytes = state.total_bytes - state.downloaded_bytes
                            if speed_bytes > 0:
                                state.eta_seconds = remaining_bytes / speed_bytes
                        
                        # Reportar progreso cada 0.5 segundos
                        now = time.time()
                        if progress_callback and (now - last_report_time) >= 0.5:
                            last_report_time = now
                            eta_min = state.eta_seconds / 60
                            msg = (f"Descargando... {state.downloaded_mb:.0f}/{state.total_mb:.0f} MB "
                                   f"({state.speed_mbps:.1f} MB/s, ~{eta_min:.0f} min restantes)")
                            progress_callback(model_id, state.progress, msg)
            
            # Descarga completa — verificar integridad
            state.status = "verificando"
            if progress_callback:
                progress_callback(model_id, 0.99, "Verificando integridad del archivo...")
            
            # Verificar tamaño
            actual_size = temp_path.stat().st_size
            expected_size = model_info.size_mb * 1024 * 1024
            # Tolerancia de 10% (los tamaños son aproximados)
            if actual_size < expected_size * 0.5:
                state.status = "error"
                state.error_message = f"Archivo incompleto ({actual_size/(1024*1024):.0f}MB vs {model_info.size_mb}MB esperados)"
                if progress_callback:
                    progress_callback(model_id, 0.0, state.error_message)
                temp_path.unlink(missing_ok=True)
                return False
            
            # Renombrar a archivo final
            if target_path.exists():
                target_path.unlink()
            temp_path.rename(target_path)
            
            # Actualizar estado
            state.status = "completo"
            self._state["installed_models"] = self.get_installed_models()
            self._save_state()
            
            if progress_callback:
                progress_callback(model_id, 1.0, f"✅ {model_info.name} instalado correctamente")
            
            return True
            
        except httpx.TimeoutException:
            state.status = "error"
            state.error_message = "Timeout — conexión muy lenta"
            if progress_callback:
                progress_callback(model_id, state.progress, 
                                 "Error: timeout. Reintenta más tarde o verifica tu internet.")
            return False
            
        except Exception as e:
            state.status = "error"
            state.error_message = str(e)
            if progress_callback:
                progress_callback(model_id, state.progress, f"Error: {e}")
            return False
    
    def download_model_async(self, model_id: str,
                             progress_callback: ProgressCallback = None) -> threading.Thread:
        """Inicia la descarga en un hilo separado (no bloquea)."""
        thread = threading.Thread(
            target=self.download_model,
            args=(model_id, progress_callback),
            daemon=True
        )
        thread.start()
        return thread
    
    def download_multiple(self, model_ids: list[str],
                          progress_callback: ProgressCallback = None) -> dict[str, bool]:
        """Descarga múltiples modelos secuencialmente."""
        results = {}
        total = len(model_ids)
        
        for i, model_id in enumerate(model_ids):
            if progress_callback:
                progress_callback(model_id, 0.0, 
                                 f"Descargando modelo {i+1}/{total}: {model_id}")
            results[model_id] = self.download_model(model_id, progress_callback)
        
        return results
    
    def get_download_state(self, model_id: str) -> Optional[DownloadState]:
        """Obtiene el estado actual de una descarga."""
        with self._download_lock:
            return self._downloads.get(model_id)
    
    def cancel_download(self, model_id: str):
        """Cancela una descarga en progreso (marca como error)."""
        with self._download_lock:
            state = self._downloads.get(model_id)
            if state:
                state.status = "error"
                state.error_message = "Cancelada por el usuario"
    
    # =================================================================
    # ELIMINACIÓN DE MODELOS
    # =================================================================
    
    def delete_model(self, model_id: str) -> bool:
        """Elimina un modelo descargado."""
        model_info = MODELS_REGISTRY.get(model_id)
        if not model_info:
            return False
        
        model_path = self.models_dir / model_info.filename
        temp_path = model_path.with_suffix(".gguf.part")
        
        try:
            if model_path.exists():
                model_path.unlink()
            if temp_path.exists():
                temp_path.unlink()
            
            # Si este era el modelo activo, detener servidor
            if self._server.current_model == model_id:
                self.stop_server()
            
            self._state["installed_models"] = self.get_installed_models()
            self._save_state()
            return True
        except Exception as e:
            print(f"Error eliminando modelo: {e}")
            return False
    
    # =================================================================
    # SERVIDOR LLAMA.CPP
    # =================================================================
    
    def get_server_executable(self) -> Optional[Path]:
        """Encuentra el ejecutable de llama-server."""
        exe_name = LLAMA_SERVER_CONFIG["executable"]
        
        # Buscar en llama-cpp/
        server_path = self.llama_dir / exe_name
        if server_path.exists():
            return server_path
        
        # Buscar en PATH
        import shutil
        found = shutil.which(exe_name)
        if found:
            return Path(found)
        
        # Buscar sin extensión en Linux
        if os.name != "nt":
            server_path = self.llama_dir / "llama-server"
            if server_path.exists():
                return server_path
        
        return None
    
    def start_server(self, model_id: str = None, 
                     port: int = None, threads: int = None, 
                     context: int = None, gpu_layers: int = 0) -> bool:
        """
        Inicia llama-server con el modelo especificado.
        
        Si ya hay un servidor corriendo con otro modelo, lo detiene primero.
        """
        # Determinar modelo a usar
        if model_id is None:
            # Usar el modelo activo o el primero instalado
            installed = self.get_installed_models()
            if not installed:
                print("❌ No hay modelos instalados")
                return False
            model_id = installed[0]
        
        model_info = MODELS_REGISTRY.get(model_id)
        if not model_info:
            print(f"❌ Modelo '{model_id}' no encontrado en el registro")
            return False
        
        model_path = self.models_dir / model_info.filename
        if not model_path.exists():
            print(f"❌ Archivo de modelo no encontrado: {model_path}")
            return False
        
        # Si ya está corriendo con el mismo modelo, no hacer nada
        if self._server.running and self._server.current_model == model_id:
            return True
        
        # Si está corriendo con otro modelo, detener primero
        if self._server.running:
            self.stop_server()
            time.sleep(1)
        
        # Encontrar ejecutable
        server_exe = self.get_server_executable()
        if not server_exe:
            print("❌ No se encontró llama-server.exe")
            return False
        
        # Configurar parámetros
        port = port or self._state.get("server_config", {}).get("port", 8080)
        threads = threads or self._state.get("server_config", {}).get("threads", 4)
        context = context or self._state.get("server_config", {}).get("context", 2048)
        
        # Construir comando
        cmd = [
            str(server_exe),
            "-m", str(model_path),
            "--port", str(port),
            "-t", str(threads),
            "-c", str(context),
            "--host", "127.0.0.1",
        ]
        
        # GPU offloading
        if gpu_layers > 0:
            cmd.extend(["-ngl", str(gpu_layers)])
        
        try:
            # Iniciar proceso
            creation_flags = 0
            if os.name == "nt":
                creation_flags = subprocess.CREATE_NO_WINDOW
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=creation_flags if os.name == "nt" else 0,
            )
            
            # Esperar a que arranque (max 15 segundos)
            for i in range(30):
                time.sleep(0.5)
                if process.poll() is not None:
                    # El proceso murió
                    stderr = process.stderr.read().decode(errors="ignore")
                    print(f"❌ llama-server murió al arrancar: {stderr[:200]}")
                    return False
                
                # Verificar si responde
                try:
                    import httpx as hx
                    r = hx.get(f"http://127.0.0.1:{port}/health", timeout=2.0)
                    if r.status_code == 200:
                        break
                except Exception:
                    continue
            else:
                print("❌ llama-server no respondió en 15 segundos")
                process.kill()
                return False
            
            # Éxito
            self._server.running = True
            self._server.pid = process.pid
            self._server.process = process
            self._server.current_model = model_id
            self._server.port = port
            self._server.threads = threads
            self._server.context_length = context
            
            self._state["active_model"] = model_id
            self._state["server_config"] = {
                "port": port,
                "threads": threads,
                "context": context,
            }
            self._save_state()
            
            print(f"✅ llama-server iniciado: {model_info.name} en puerto {port}")
            return True
            
        except Exception as e:
            print(f"❌ Error iniciando llama-server: {e}")
            return False
    
    def stop_server(self) -> bool:
        """Detiene el servidor llama.cpp."""
        if not self._server.running:
            return True
        
        try:
            if self._server.process:
                self._server.process.terminate()
                try:
                    self._server.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self._server.process.kill()
            
            self._server.running = False
            self._server.current_model = ""
            self._server.process = None
            self._server.pid = 0
            print("🛑 llama-server detenido")
            return True
        except Exception as e:
            print(f"⚠️ Error deteniendo servidor: {e}")
            return False
    
    def switch_model(self, model_id: str) -> bool:
        """
        Hot-swap: cambia el modelo activo reiniciando llama-server.
        
        Detiene el servidor actual y lo reinicia con el nuevo modelo.
        """
        if self._server.current_model == model_id and self._server.running:
            return True  # Ya está corriendo ese modelo
        
        if not self.is_model_installed(model_id):
            print(f"❌ Modelo '{model_id}' no está instalado")
            return False
        
        print(f"🔄 Cambiando modelo a: {model_id}...")
        return self.start_server(
            model_id=model_id,
            port=self._server.port,
            threads=self._server.threads,
            context=self._server.context_length,
        )
    
    def is_server_running(self) -> bool:
        """Verifica si el servidor está respondiendo."""
        if not self._server.running:
            return False
        
        try:
            import httpx as hx
            r = hx.get(f"http://127.0.0.1:{self._server.port}/health", timeout=2.0)
            return r.status_code == 200
        except Exception:
            self._server.running = False
            return False
    
    def get_server_status(self) -> dict:
        """Devuelve el estado actual del servidor."""
        running = self.is_server_running()
        return {
            "running": running,
            "model": self._server.current_model if running else "",
            "port": self._server.port,
            "threads": self._server.threads,
            "context": self._server.context_length,
            "pid": self._server.pid if running else 0,
        }
    
    # =================================================================
    # UTILIDADES
    # =================================================================
    
    def get_disk_usage(self) -> dict:
        """Calcula el espacio usado por modelos."""
        total_bytes = 0
        models_size = {}
        
        for model_id in self.get_installed_models():
            info = MODELS_REGISTRY.get(model_id)
            if info:
                path = self.models_dir / info.filename
                if path.exists():
                    size = path.stat().st_size
                    total_bytes += size
                    models_size[model_id] = round(size / (1024 * 1024))
        
        return {
            "total_mb": round(total_bytes / (1024 * 1024)),
            "total_gb": round(total_bytes / (1024**3), 2),
            "por_modelo": models_size,
        }
    
    def verify_model_integrity(self, model_id: str) -> bool:
        """Verifica que un modelo no esté corrupto (verificación rápida por tamaño)."""
        info = MODELS_REGISTRY.get(model_id)
        if not info:
            return False
        
        path = self.models_dir / info.filename
        if not path.exists():
            return False
        
        actual_mb = path.stat().st_size / (1024 * 1024)
        # Tolerancia de 20% (quantization puede variar)
        return actual_mb >= info.size_mb * 0.5
    
    def get_best_model_for_ram(self, available_ram_gb: float) -> Optional[str]:
        """Devuelve el mejor modelo instalado que cabe en la RAM disponible."""
        installed = self.get_installed_models()
        best = None
        best_size = 0
        
        for model_id in installed:
            info = MODELS_REGISTRY.get(model_id)
            if info and info.ram_required_gb <= (available_ram_gb - 1.5):
                if info.size_mb > best_size:
                    best = model_id
                    best_size = info.size_mb
        
        # Si ninguno cabe bien, usar el más pequeño instalado
        if not best and installed:
            smallest = min(installed, 
                          key=lambda m: MODELS_REGISTRY[m].size_mb if m in MODELS_REGISTRY else 9999)
            best = smallest
        
        return best
    
    def mark_first_run_complete(self):
        """Marca que la primera ejecución (setup) se completó."""
        self._state["first_run_complete"] = True
        self._save_state()
    
    def is_first_run(self) -> bool:
        """Verifica si es la primera ejecución (no se han descargado modelos)."""
        return not self._state.get("first_run_complete", False)


# === INSTANCIA GLOBAL (singleton) ===
_manager_instance: Optional[ModelManager] = None


def get_model_manager() -> ModelManager:
    """Obtiene la instancia global del ModelManager."""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = ModelManager()
    return _manager_instance


# === EJECUCIÓN DIRECTA PARA PRUEBAS ===
if __name__ == "__main__":
    print("=" * 60)
    print("  ASTRA — Gestor de Modelos")
    print("=" * 60)
    
    manager = get_model_manager()
    
    print("\n  Modelos disponibles:")
    for model in manager.list_available_models():
        status = "✅ Instalado" if model["installed"] else "⬇️ No descargado"
        print(f"    [{status}] {model['name']} ({model['size_mb']}MB) — {model['description']}")
    
    installed = manager.get_installed_models()
    print(f"\n  Modelos instalados: {len(installed)}")
    for m in installed:
        print(f"    • {m}")
    
    usage = manager.get_disk_usage()
    print(f"\n  Espacio usado por modelos: {usage['total_gb']} GB")
    
    server = manager.get_server_status()
    print(f"\n  Servidor: {'🟢 Activo' if server['running'] else '🔴 Detenido'}")
    if server['running']:
        print(f"    Modelo: {server['model']}")
        print(f"    Puerto: {server['port']}")
    
    print()
