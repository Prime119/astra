"""
ASTRA Installer — Selector de Modelos (GUI).

Interfaz gráfica con tkinter (incluido en Python) que muestra:
- Hardware detectado del sistema
- Modelos recomendados vs todos disponibles
- Selector interactivo con checkboxes
- Barra de progreso para descargas
- Indicadores de cuál es más ligero/pesado

Compatible con Windows 11 sin dependencias extra.
"""
from __future__ import annotations

import sys
import threading
import time
from pathlib import Path
from typing import Optional

try:
    import tkinter as tk
    from tkinter import ttk, messagebox
    TK_AVAILABLE = True
except ImportError:
    TK_AVAILABLE = False

from installer.hardware_detect import full_hardware_scan, hardware_report_to_dict, HardwareReport
from installer.model_manager import ModelManager, get_model_manager
from installer.config import MODELS_REGISTRY, get_total_download_size



# === COLORES ESTILO ASTRA (tema oscuro futurista) ===
COLORS = {
    "bg": "#0a0e14",
    "bg_secondary": "#111820",
    "bg_card": "#151c26",
    "accent": "#00d4ff",
    "accent_hover": "#33e0ff",
    "success": "#00ff88",
    "warning": "#ffaa00",
    "danger": "#ff4444",
    "text": "#e0e8f0",
    "text_dim": "#7a8a9a",
    "border": "#1e2a38",
}


class ModelSelectorUI:
    """Interfaz gráfica del selector de modelos de Astra."""

    def __init__(self, hardware_report: HardwareReport = None):
        if not TK_AVAILABLE:
            raise RuntimeError("tkinter no disponible")

        self.report = hardware_report or full_hardware_scan()
        self.hw_info = hardware_report_to_dict(self.report)
        self.manager = get_model_manager()
        self.selected_models: dict[str, tk.BooleanVar] = {}
        self.download_active = False
        self.result_models: list[str] = []  # Modelos seleccionados al cerrar

        self._build_window()

    def _build_window(self):
        """Construye la ventana principal."""
        self.root = tk.Tk()
        self.root.title("ASTRA — Configuración de Modelos")
        self.root.geometry("900x680")
        self.root.configure(bg=COLORS["bg"])
        self.root.resizable(True, True)

        # Intentar centrar en pantalla
        self.root.update_idletasks()
        w = 900
        h = 680
        x = (self.root.winfo_screenwidth() // 2) - (w // 2)
        y = (self.root.winfo_screenheight() // 2) - (h // 2)
        self.root.geometry(f"{w}x{h}+{x}+{y}")

        # Estilo ttk
        self._configure_styles()

        # Layout principal
        self._build_header()
        self._build_hardware_panel()
        self._build_models_panel()
        self._build_footer()


    def _configure_styles(self):
        """Configura estilos ttk para tema oscuro."""
        style = ttk.Style()
        style.theme_use("clam")

        style.configure("Dark.TFrame", background=COLORS["bg"])
        style.configure("Card.TFrame", background=COLORS["bg_card"])
        style.configure("Dark.TLabel",
                        background=COLORS["bg"],
                        foreground=COLORS["text"],
                        font=("Segoe UI", 10))
        style.configure("Title.TLabel",
                        background=COLORS["bg"],
                        foreground=COLORS["accent"],
                        font=("Segoe UI", 18, "bold"))
        style.configure("Subtitle.TLabel",
                        background=COLORS["bg"],
                        foreground=COLORS["text_dim"],
                        font=("Segoe UI", 9))
        style.configure("Card.TLabel",
                        background=COLORS["bg_card"],
                        foreground=COLORS["text"],
                        font=("Segoe UI", 9))
        style.configure("CardTitle.TLabel",
                        background=COLORS["bg_card"],
                        foreground=COLORS["accent"],
                        font=("Segoe UI", 10, "bold"))
        style.configure("Accent.TButton",
                        background=COLORS["accent"],
                        foreground="#000000",
                        font=("Segoe UI", 11, "bold"),
                        padding=(20, 10))
        style.configure("Dark.TCheckbutton",
                        background=COLORS["bg_card"],
                        foreground=COLORS["text"],
                        font=("Segoe UI", 10))
        style.configure("green.Horizontal.TProgressbar",
                        troughcolor=COLORS["bg_secondary"],
                        background=COLORS["success"])

    def _build_header(self):
        """Construye el encabezado con título y descripción."""
        header = ttk.Frame(self.root, style="Dark.TFrame")
        header.pack(fill="x", padx=30, pady=(20, 10))

        ttk.Label(header, text="ASTRA — Selector de Modelos",
                  style="Title.TLabel").pack(anchor="w")
        ttk.Label(header,
                  text="Elige los modelos de IA que quieres descargar. "
                       "Astra seleccionará automáticamente el mejor según la tarea.",
                  style="Subtitle.TLabel").pack(anchor="w", pady=(4, 0))


    def _build_hardware_panel(self):
        """Panel de información de hardware detectado."""
        hw_frame = ttk.Frame(self.root, style="Card.TFrame")
        hw_frame.pack(fill="x", padx=30, pady=(5, 10))

        # Padding interno
        inner = ttk.Frame(hw_frame, style="Card.TFrame")
        inner.pack(fill="x", padx=15, pady=10)

        ttk.Label(inner, text="Hardware Detectado",
                  style="CardTitle.TLabel").pack(anchor="w")

        info = self.hw_info
        hw_text = (
            f"CPU: {info['cpu']['nombre']}  |  "
            f"RAM: {info['ram']['total_gb']} GB  |  "
            f"GPU: {info['gpu']['nombre']}  |  "
            f"Disco libre: {info['disco']['libre_gb']} GB"
        )
        ttk.Label(inner, text=hw_text, style="Card.TLabel").pack(anchor="w", pady=(4, 0))

        # Tier y recomendación
        tier = info['tier'].upper()
        tier_colors = {"LOW": COLORS["warning"], "MID": COLORS["accent"], "HIGH": COLORS["success"]}
        tier_label = ttk.Label(inner,
                               text=f"Clasificación: {tier} — {info['tier_descripcion']}",
                               style="Card.TLabel")
        tier_label.pack(anchor="w", pady=(4, 0))

        # Advertencias
        if info['advertencias']:
            for warn in info['advertencias']:
                ttk.Label(inner, text=f"⚠️ {warn}",
                          style="Card.TLabel").pack(anchor="w")


    def _build_models_panel(self):
        """Panel principal con la lista de modelos seleccionables."""
        models_frame = ttk.Frame(self.root, style="Dark.TFrame")
        models_frame.pack(fill="both", expand=True, padx=30, pady=(5, 10))

        # Canvas con scrollbar para la lista
        canvas = tk.Canvas(models_frame, bg=COLORS["bg"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(models_frame, orient="vertical", command=canvas.yview)
        self.models_container = ttk.Frame(canvas, style="Dark.TFrame")

        self.models_container.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=self.models_container, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Generar tarjetas de modelos
        recommended = self.hw_info["modelos_recomendados"]
        installed = self.manager.get_installed_models()

        # Encontrar más ligero y más pesado
        all_models = list(MODELS_REGISTRY.items())
        lightest = min(all_models, key=lambda x: x[1].size_mb)[0]
        heaviest = max(all_models, key=lambda x: x[1].size_mb)[0]

        for model_id, model_info in MODELS_REGISTRY.items():
            if not model_info.download_url and model_id not in installed:
                continue  # Saltar modelos sin URL que no están instalados

            self._build_model_card(
                model_id, model_info,
                is_recommended=(model_id in recommended),
                is_installed=(model_id in installed),
                is_lightest=(model_id == lightest),
                is_heaviest=(model_id == heaviest),
            )


    def _build_model_card(self, model_id: str, model_info, 
                          is_recommended: bool, is_installed: bool,
                          is_lightest: bool, is_heaviest: bool):
        """Construye una tarjeta individual de modelo."""
        card = ttk.Frame(self.models_container, style="Card.TFrame")
        card.pack(fill="x", pady=4, padx=5)

        inner = ttk.Frame(card, style="Card.TFrame")
        inner.pack(fill="x", padx=12, pady=8)

        # Fila superior: checkbox + nombre + badges
        top_row = ttk.Frame(inner, style="Card.TFrame")
        top_row.pack(fill="x")

        # Checkbox
        var = tk.BooleanVar(value=is_recommended or is_installed)
        self.selected_models[model_id] = var

        cb = ttk.Checkbutton(
            top_row, text=model_info.name,
            variable=var, style="Dark.TCheckbutton",
            command=self._update_summary
        )
        cb.pack(side="left")

        # Badges
        badges_frame = ttk.Frame(top_row, style="Card.TFrame")
        badges_frame.pack(side="right")

        if is_installed:
            tk.Label(badges_frame, text=" ✅ Instalado ", bg="#004422",
                     fg=COLORS["success"], font=("Segoe UI", 8)).pack(side="right", padx=2)
        if is_recommended and not is_installed:
            tk.Label(badges_frame, text=" ⭐ Recomendado ", bg="#1a3050",
                     fg=COLORS["accent"], font=("Segoe UI", 8)).pack(side="right", padx=2)
        if is_lightest:
            tk.Label(badges_frame, text=" 🪶 Más ligero ", bg="#2a2a00",
                     fg=COLORS["warning"], font=("Segoe UI", 8)).pack(side="right", padx=2)
        if is_heaviest:
            tk.Label(badges_frame, text=" 🏋️ Más pesado ", bg="#2a1a1a",
                     fg=COLORS["danger"], font=("Segoe UI", 8)).pack(side="right", padx=2)

        # Fila inferior: descripción + specs
        desc_text = f"{model_info.description}"
        ttk.Label(inner, text=desc_text, style="Card.TLabel").pack(anchor="w", pady=(2, 0))

        specs_text = (
            f"📦 {model_info.size_mb} MB  |  "
            f"🧠 RAM min: {model_info.ram_required_gb} GB  |  "
            f"⚡ {model_info.speed}  |  "
            f"📊 Calidad: {model_info.quality}  |  "
            f"🏷️ {model_info.category}"
        )
        ttk.Label(inner, text=specs_text, style="Card.TLabel").pack(anchor="w")


    def _build_footer(self):
        """Panel inferior con resumen y botón de descarga."""
        footer = ttk.Frame(self.root, style="Dark.TFrame")
        footer.pack(fill="x", padx=30, pady=(5, 20))

        # Resumen de descarga
        self.summary_label = ttk.Label(footer, text="", style="Dark.TLabel")
        self.summary_label.pack(anchor="w")

        # Barra de progreso (oculta hasta que se descargue)
        self.progress_frame = ttk.Frame(footer, style="Dark.TFrame")

        self.progress_bar = ttk.Progressbar(
            self.progress_frame, style="green.Horizontal.TProgressbar",
            orient="horizontal", length=400, mode="determinate"
        )
        self.progress_bar.pack(fill="x", pady=(5, 2))

        self.progress_label = ttk.Label(self.progress_frame, text="",
                                        style="Subtitle.TLabel")
        self.progress_label.pack(anchor="w")

        # Botones
        btn_frame = ttk.Frame(footer, style="Dark.TFrame")
        btn_frame.pack(fill="x", pady=(10, 0))

        self.btn_download = ttk.Button(
            btn_frame, text="Descargar e Instalar",
            style="Accent.TButton", command=self._start_downloads
        )
        self.btn_download.pack(side="right")

        self.btn_skip = ttk.Button(
            btn_frame, text="Omitir (usar modelo existente)",
            command=self._skip_download
        )
        self.btn_skip.pack(side="right", padx=(0, 10))

        # Actualizar resumen inicial
        self._update_summary()

    def _update_summary(self):
        """Actualiza el texto resumen de lo que se va a descargar."""
        selected = [mid for mid, var in self.selected_models.items() if var.get()]
        installed = self.manager.get_installed_models()

        to_download = [m for m in selected if m not in installed]
        total_mb = get_total_download_size(to_download)

        if not to_download:
            if selected:
                self.summary_label.config(
                    text=f"✅ {len(selected)} modelo(s) seleccionado(s) — todos ya instalados"
                )
            else:
                self.summary_label.config(text="Selecciona al menos un modelo para continuar")
        else:
            total_gb = total_mb / 1024
            self.summary_label.config(
                text=f"⬇️ {len(to_download)} modelo(s) por descargar — {total_gb:.1f} GB total"
            )


    def _start_downloads(self):
        """Inicia la descarga de modelos seleccionados."""
        selected = [mid for mid, var in self.selected_models.items() if var.get()]
        installed = self.manager.get_installed_models()
        to_download = [m for m in selected if m not in installed]

        if not selected:
            messagebox.showwarning("Sin selección",
                                   "Selecciona al menos un modelo para continuar.")
            return

        if not to_download:
            # Todos ya instalados — cerrar y continuar
            self.result_models = selected
            self.root.destroy()
            return

        # Mostrar barra de progreso
        self.progress_frame.pack(fill="x", pady=(5, 0))
        self.btn_download.config(state="disabled")
        self.download_active = True

        # Descargar en hilo separado
        thread = threading.Thread(
            target=self._download_thread,
            args=(to_download, selected),
            daemon=True
        )
        thread.start()

    def _download_thread(self, to_download: list[str], all_selected: list[str]):
        """Hilo de descarga de modelos."""
        total = len(to_download)
        success_count = 0

        for i, model_id in enumerate(to_download):
            if not self.download_active:
                break

            model_info = MODELS_REGISTRY.get(model_id)
            model_name = model_info.name if model_info else model_id

            def progress_cb(mid, progress, message):
                # Actualizar UI desde el hilo (thread-safe con after)
                overall = (i + progress) / total
                self.root.after(0, self._update_progress, overall, message, mid)

            progress_cb(model_id, 0.0, f"Iniciando descarga de {model_name}...")
            success = self.manager.download_model(model_id, progress_cb)

            if success:
                success_count += 1

        # Finalizar
        self.root.after(0, self._downloads_complete, success_count, total, all_selected)

    def _update_progress(self, overall_progress: float, message: str, model_id: str):
        """Actualiza la barra de progreso (llamado desde el hilo principal)."""
        self.progress_bar["value"] = overall_progress * 100
        self.progress_label.config(text=message)

    def _downloads_complete(self, success: int, total: int, all_selected: list[str]):
        """Callback cuando terminan todas las descargas."""
        self.download_active = False
        self.btn_download.config(state="normal")

        if success == total:
            self.progress_label.config(text=f"✅ ¡{success} modelo(s) descargado(s) correctamente!")
            self.progress_bar["value"] = 100

            # Marcar primera ejecución como completa
            self.manager.mark_first_run_complete()
            self.result_models = all_selected

            # Cerrar después de 2 segundos
            self.root.after(2000, self.root.destroy)
        else:
            failed = total - success
            self.progress_label.config(
                text=f"⚠️ {success}/{total} descargados. {failed} fallaron. "
                     f"Puedes reintentar o continuar con lo disponible."
            )
            self.btn_download.config(text="Reintentar fallidos")
            self.result_models = all_selected

    def _skip_download(self):
        """Omite la descarga y usa modelos existentes."""
        installed = self.manager.get_installed_models()
        if installed:
            self.result_models = installed
            self.manager.mark_first_run_complete()
            self.root.destroy()
        else:
            messagebox.showwarning(
                "Sin modelos",
                "No hay modelos instalados. Necesitas descargar al menos uno "
                "para que Astra funcione."
            )


    def run(self) -> list[str]:
        """Ejecuta la UI y devuelve la lista de modelos seleccionados."""
        self.root.mainloop()
        return self.result_models


def show_model_selector(hardware_report: HardwareReport = None) -> list[str]:
    """
    Función de alto nivel: muestra el selector de modelos y devuelve
    los IDs de modelos seleccionados por el usuario.
    
    Returns:
        Lista de model_ids seleccionados (vacía si se canceló)
    """
    if not TK_AVAILABLE:
        print("⚠️ tkinter no disponible. Usando selección por consola.")
        return _console_selector(hardware_report)

    try:
        ui = ModelSelectorUI(hardware_report)
        return ui.run()
    except Exception as e:
        print(f"⚠️ Error en UI gráfica: {e}")
        print("   Usando selección por consola...")
        return _console_selector(hardware_report)


def _console_selector(hardware_report: HardwareReport = None) -> list[str]:
    """Selector de modelos por consola (fallback si tkinter no funciona)."""
    from installer.hardware_detect import full_hardware_scan, hardware_report_to_dict

    report = hardware_report or full_hardware_scan()
    info = hardware_report_to_dict(report)

    print("\n" + "=" * 60)
    print("  ASTRA — Selector de Modelos (modo consola)")
    print("=" * 60)
    print(f"\n  Tu PC: {info['ram']['total_gb']}GB RAM | {info['gpu']['nombre']} | "
          f"{info['disco']['libre_gb']}GB disco libre")
    print(f"  Tier: {info['tier'].upper()} — {info['tier_descripcion']}")

    print("\n  Modelos disponibles:")
    print("  " + "-" * 50)

    models_list = []
    recommended = info["modelos_recomendados"]
    manager = get_model_manager()
    installed = manager.get_installed_models()

    for i, (model_id, model_info) in enumerate(MODELS_REGISTRY.items(), 1):
        if not model_info.download_url and model_id not in installed:
            continue
        models_list.append(model_id)
        rec = " ⭐" if model_id in recommended else ""
        inst = " ✅" if model_id in installed else ""
        print(f"  {i}. {model_info.name} ({model_info.size_mb}MB){rec}{inst}")
        print(f"     {model_info.description}")

    print("\n  Ingresa los números separados por coma (ej: 1,2,3)")
    print("  O presiona Enter para usar los recomendados:")

    try:
        choice = input("  > ").strip()
    except (EOFError, KeyboardInterrupt):
        choice = ""

    if not choice:
        return [m for m in recommended if m in models_list]

    try:
        indices = [int(x.strip()) - 1 for x in choice.split(",")]
        selected = [models_list[i] for i in indices if 0 <= i < len(models_list)]
        return selected if selected else recommended
    except (ValueError, IndexError):
        return [m for m in recommended if m in models_list]


# === EJECUCIÓN DIRECTA PARA PRUEBAS ===
if __name__ == "__main__":
    print("Iniciando selector de modelos...")
    selected = show_model_selector()
    print(f"\nModelos seleccionados: {selected}")
