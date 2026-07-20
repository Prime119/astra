"""
ASTRA Installer — Flujo de Primera Ejecución.

Orquesta la experiencia de primer arranque:
1. Escaneo de hardware
2. Verificación de llama-server.exe
3. Selector de modelos (GUI)
4. Descarga de modelos seleccionados
5. Configuración de llama-server óptima
6. Arranque de Astra

Se ejecuta automáticamente si no hay modelos instalados.
Puede re-ejecutarse manualmente desde el menú de configuración.
"""
from __future__ import annotations

import sys
import os
import json
import time
import shutil
from pathlib import Path
from typing import Optional

# Asegurar que el path del proyecto esté disponible
ASTRA_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ASTRA_ROOT))
sys.path.insert(0, str(ASTRA_ROOT / "src"))



from installer.config import (
    MODELS_DIR, LLAMA_CPP_DIR, CONFIG_DIR, INSTALLER_STATE_FILE,
    LLAMA_SERVER_CONFIG, INSTALLER_CONFIG, MODELS_REGISTRY,
    get_installed_models,
)
from installer.hardware_detect import (
    full_hardware_scan, hardware_report_to_dict, HardwareReport,
)
from installer.model_manager import ModelManager, get_model_manager


class FirstRunSetup:
    """
    Gestiona el flujo completo de primera ejecución de Astra.
    
    Pasos:
    1. Verificar prerrequisitos (llama-server.exe)
    2. Escanear hardware
    3. Mostrar selector de modelos
    4. Descargar modelos seleccionados
    5. Configurar y arrancar llama-server
    """

    def __init__(self):
        self.manager = get_model_manager()
        self.hardware_report: Optional[HardwareReport] = None
        self.selected_models: list[str] = []
        self.setup_complete = False
        self._log_lines: list[str] = []

    def _log(self, message: str):
        """Log interno del setup."""
        self._log_lines.append(message)
        print(f"  [Setup] {message}")

    # =================================================================
    # PASO 1: VERIFICAR PRERREQUISITOS
    # =================================================================

    def check_prerequisites(self) -> dict:
        """
        Verifica que estén disponibles los componentes necesarios.
        
        Returns:
            Dict con estado de cada componente y si se puede continuar.
        """
        results = {
            "llama_server": False,
            "models_dir": False,
            "config_dir": False,
            "can_continue": False,
            "issues": [],
        }

        # Verificar llama-server.exe
        exe_name = LLAMA_SERVER_CONFIG["executable"]
        server_path = LLAMA_CPP_DIR / exe_name

        if server_path.exists():
            results["llama_server"] = True
            self._log(f"✅ {exe_name} encontrado en {LLAMA_CPP_DIR}")
        else:
            # Buscar en PATH
            found = shutil.which(exe_name)
            if found:
                results["llama_server"] = True
                self._log(f"✅ {exe_name} encontrado en PATH: {found}")
            else:
                results["issues"].append(
                    f"❌ {exe_name} no encontrado. "
                    f"Debe estar en {LLAMA_CPP_DIR}/ o en el PATH del sistema."
                )
                self._log(f"❌ {exe_name} no encontrado")

        # Verificar/crear directorio de modelos
        try:
            MODELS_DIR.mkdir(parents=True, exist_ok=True)
            results["models_dir"] = True
            self._log(f"✅ Directorio de modelos: {MODELS_DIR}")
        except Exception as e:
            results["issues"].append(f"❌ No se puede crear {MODELS_DIR}: {e}")

        # Verificar/crear directorio de config
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            results["config_dir"] = True
            self._log(f"✅ Directorio de config: {CONFIG_DIR}")
        except Exception as e:
            results["issues"].append(f"❌ No se puede crear {CONFIG_DIR}: {e}")

        # Determinar si se puede continuar
        results["can_continue"] = results["llama_server"] and results["models_dir"]

        return results


    # =================================================================
    # PASO 2: ESCANEAR HARDWARE
    # =================================================================

    def scan_hardware(self) -> HardwareReport:
        """Escanea el hardware y genera recomendaciones."""
        self._log("🔍 Escaneando hardware...")
        self.hardware_report = full_hardware_scan()
        info = hardware_report_to_dict(self.hardware_report)

        self._log(f"   RAM: {info['ram']['total_gb']} GB")
        self._log(f"   CPU: {info['cpu']['nombre']} ({info['cpu']['nucleos_fisicos']} núcleos)")
        self._log(f"   GPU: {info['gpu']['nombre']}")
        self._log(f"   Disco libre: {info['disco']['libre_gb']} GB")
        self._log(f"   Tier: {info['tier'].upper()} — {info['tier_descripcion']}")
        self._log(f"   Modelos recomendados: {len(info['modelos_recomendados'])}")

        return self.hardware_report

    # =================================================================
    # PASO 3: MOSTRAR SELECTOR DE MODELOS
    # =================================================================

    def show_model_selector(self) -> list[str]:
        """Muestra la UI de selección de modelos."""
        self._log("📋 Mostrando selector de modelos...")

        from installer.ui_selector import show_model_selector
        self.selected_models = show_model_selector(self.hardware_report)

        if self.selected_models:
            self._log(f"✅ Modelos seleccionados: {', '.join(self.selected_models)}")
        else:
            self._log("⚠️ No se seleccionaron modelos")

        return self.selected_models

    # =================================================================
    # PASO 4: DESCARGAR MODELOS
    # =================================================================

    def download_selected_models(self, 
                                  progress_callback=None) -> dict[str, bool]:
        """
        Descarga los modelos seleccionados que no estén instalados.
        
        Returns:
            Dict {model_id: success_bool}
        """
        installed = self.manager.get_installed_models()
        to_download = [m for m in self.selected_models 
                       if m not in installed and MODELS_REGISTRY.get(m, None) 
                       and MODELS_REGISTRY[m].download_url]

        if not to_download:
            self._log("✅ Todos los modelos seleccionados ya están instalados")
            return {m: True for m in self.selected_models}

        total_mb = sum(MODELS_REGISTRY[m].size_mb for m in to_download)
        self._log(f"⬇️ Descargando {len(to_download)} modelo(s) ({total_mb/1024:.1f} GB)...")

        results = {}
        for i, model_id in enumerate(to_download, 1):
            info = MODELS_REGISTRY[model_id]
            self._log(f"   [{i}/{len(to_download)}] {info.name} ({info.size_mb}MB)...")

            def _cb(mid, progress, message):
                if progress_callback:
                    overall = ((i - 1) + progress) / len(to_download)
                    progress_callback(mid, overall, message)

            success = self.manager.download_model(model_id, _cb)
            results[model_id] = success

            if success:
                self._log(f"   ✅ {info.name} descargado")
            else:
                self._log(f"   ❌ {info.name} falló")

        return results


    # =================================================================
    # PASO 5: CONFIGURAR Y ARRANCAR SERVIDOR
    # =================================================================

    def configure_and_start_server(self) -> bool:
        """
        Configura llama-server con los parámetros óptimos y lo inicia.
        
        Usa la info de hardware para determinar threads y contexto.
        """
        if not self.hardware_report:
            self.scan_hardware()

        info = hardware_report_to_dict(self.hardware_report)
        threads = info["threads_optimos"]
        context = info["contexto_optimo"]

        # Determinar modelo inicial (el más rápido para primer arranque)
        installed = self.manager.get_installed_models()
        if not installed:
            self._log("❌ No hay modelos instalados — no se puede iniciar servidor")
            return False

        # Preferir el modelo rápido para arranque
        startup_model = None
        for preferred in ["qwen2.5-1.5b-instruct", "qwen2.5-3b-instruct", "qwen2.5-3b"]:
            if preferred in installed:
                startup_model = preferred
                break
        if not startup_model:
            startup_model = installed[0]

        self._log(f"🚀 Iniciando llama-server...")
        self._log(f"   Modelo: {startup_model}")
        self._log(f"   Threads: {threads}")
        self._log(f"   Contexto: {context}")
        self._log(f"   Puerto: 8080")

        # GPU layers
        gpu_layers = 0
        if info["gpu"]["vendor"] == "nvidia" and info["gpu"]["vram_gb"] >= 2.0:
            gpu_layers = 20  # Offload parcial a GPU
            self._log(f"   GPU offload: {gpu_layers} capas")

        success = self.manager.start_server(
            model_id=startup_model,
            port=8080,
            threads=threads,
            context=context,
            gpu_layers=gpu_layers,
        )

        if success:
            self._log("✅ Servidor llama.cpp iniciado correctamente")
        else:
            self._log("❌ No se pudo iniciar el servidor")

        return success

    # =================================================================
    # PASO 6: GUARDAR CONFIGURACIÓN FINAL
    # =================================================================

    def save_setup_config(self):
        """Guarda la configuración generada por el setup."""
        if not self.hardware_report:
            return

        info = hardware_report_to_dict(self.hardware_report)

        setup_config = {
            "setup_complete": True,
            "setup_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "hardware": {
                "tier": info["tier"],
                "ram_gb": info["ram"]["total_gb"],
                "gpu": info["gpu"]["nombre"],
                "gpu_vendor": info["gpu"]["vendor"],
            },
            "server": {
                "threads": info["threads_optimos"],
                "context": info["contexto_optimo"],
                "port": 8080,
            },
            "models": {
                "installed": self.manager.get_installed_models(),
                "selected": self.selected_models,
            },
        }

        config_file = CONFIG_DIR / "setup_result.json"
        try:
            config_file.write_text(
                json.dumps(setup_config, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
            self._log(f"✅ Configuración guardada en {config_file}")
        except Exception as e:
            self._log(f"⚠️ No se pudo guardar config: {e}")

        # Marcar primera ejecución como completa
        self.manager.mark_first_run_complete()
        self.setup_complete = True


    # =================================================================
    # EJECUCIÓN COMPLETA
    # =================================================================

    def run_full_setup(self, skip_ui: bool = False) -> bool:
        """
        Ejecuta el flujo completo de primera ejecución.
        
        Args:
            skip_ui: Si True, usa modelos recomendados sin mostrar UI
            
        Returns:
            True si el setup fue exitoso
        """
        print()
        print("=" * 60)
        print("  🌟 ASTRA — Configuración Inicial")
        print("=" * 60)
        print()

        # Paso 1: Prerrequisitos
        self._log("Paso 1/5: Verificando prerrequisitos...")
        prereqs = self.check_prerequisites()

        if not prereqs["can_continue"]:
            print()
            print("  ❌ No se puede continuar con el setup:")
            for issue in prereqs["issues"]:
                print(f"     {issue}")
            print()
            print("  Solución: Asegúrate de tener llama-server.exe en la carpeta llama-cpp/")
            return False

        # Paso 2: Hardware
        print()
        self._log("Paso 2/5: Escaneando hardware...")
        self.scan_hardware()

        # Paso 3: Selector de modelos
        print()
        self._log("Paso 3/5: Selección de modelos...")

        if skip_ui:
            # Usar modelos recomendados directamente
            info = hardware_report_to_dict(self.hardware_report)
            self.selected_models = info["modelos_recomendados"]
            self._log(f"   Auto-seleccionados: {', '.join(self.selected_models)}")
        else:
            self.show_model_selector()

        if not self.selected_models:
            self._log("⚠️ No se seleccionaron modelos. Abortando setup.")
            return False

        # Paso 4: Descargar
        print()
        self._log("Paso 4/5: Descargando modelos...")
        results = self.download_selected_models()

        # Verificar que al menos un modelo se descargó
        any_success = any(results.values()) or bool(self.manager.get_installed_models())
        if not any_success:
            self._log("❌ No se pudo descargar ningún modelo.")
            self._log("   Verifica tu conexión a internet e intenta de nuevo.")
            return False

        # Paso 5: Configurar y arrancar
        print()
        self._log("Paso 5/5: Configurando servidor...")
        server_ok = self.configure_and_start_server()

        # Guardar configuración
        self.save_setup_config()

        # Resumen final
        print()
        print("=" * 60)
        if server_ok:
            installed = self.manager.get_installed_models()
            print("  ✅ ¡ASTRA está lista!")
            print(f"  📦 Modelos instalados: {len(installed)}")
            for m in installed:
                info = MODELS_REGISTRY.get(m)
                name = info.name if info else m
                print(f"     • {name}")
            print(f"  🧠 Modelo activo: {self.manager.get_server_status().get('model', 'N/A')}")
            print(f"  🌐 Servidor: http://127.0.0.1:8080")
            print()
            print("  Astra seleccionará automáticamente el mejor modelo")
            print("  según cada tarea. ¡100% local, sin internet!")
        else:
            print("  ⚠️ Setup parcial — modelos descargados pero servidor no arrancó.")
            print("  Inicia manualmente: llama-server.exe -m models/[modelo].gguf --port 8080")
        print("=" * 60)
        print()

        return server_ok


# =================================================================
# FUNCIONES DE ALTO NIVEL
# =================================================================

def needs_first_run() -> bool:
    """Verifica si se necesita ejecutar el setup de primera vez."""
    manager = get_model_manager()

    # Si ya se completó el first-run, no repetir
    if not manager.is_first_run():
        return False

    # Si hay modelos instalados, probablemente no es primera vez
    installed = manager.get_installed_models()
    if installed:
        # Marcar como completado y no volver a preguntar
        manager.mark_first_run_complete()
        return False

    return True


def run_first_time_setup(skip_ui: bool = False) -> bool:
    """
    Ejecuta el setup de primera vez si es necesario.
    
    Returns:
        True si el setup se completó (o no era necesario)
    """
    if not needs_first_run():
        return True

    setup = FirstRunSetup()
    return setup.run_full_setup(skip_ui=skip_ui)


def run_model_manager_ui():
    """
    Abre la UI de gestión de modelos (para agregar/quitar después del setup).
    """
    from installer.ui_selector import show_model_selector
    report = full_hardware_scan()
    selected = show_model_selector(report)

    if selected:
        manager = get_model_manager()
        installed = manager.get_installed_models()
        to_download = [m for m in selected if m not in installed]

        if to_download:
            print(f"Descargando {len(to_download)} modelo(s)...")
            for model_id in to_download:
                def _cb(mid, progress, msg):
                    print(f"\r  {msg}", end="", flush=True)
                manager.download_model(model_id, _cb)
                print()
            print("✅ Descarga completada")


# === EJECUCIÓN DIRECTA ===
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="ASTRA — Setup de primera ejecución")
    parser.add_argument("--no-ui", action="store_true",
                        help="Usar modelos recomendados sin mostrar UI")
    parser.add_argument("--force", action="store_true",
                        help="Forzar setup aunque ya se haya ejecutado")
    parser.add_argument("--manage", action="store_true",
                        help="Abrir gestor de modelos (agregar/quitar)")

    args = parser.parse_args()

    if args.manage:
        run_model_manager_ui()
    elif args.force or needs_first_run():
        setup = FirstRunSetup()
        setup.run_full_setup(skip_ui=args.no_ui)
    else:
        print("✅ El setup ya fue completado. Usa --force para re-ejecutar o --manage para gestionar modelos.")
