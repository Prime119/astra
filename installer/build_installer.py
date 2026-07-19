"""
ASTRA — Build Automation Script.

Automatiza la creación del instalador .exe:
1. Descarga Python embebido (3.11.x, ~15MB)
2. Instala pip en Python embebido
3. Instala dependencias de Astra en Python embebido
4. Descarga llama-server.exe pre-compilado
5. Empaqueta Electron con electron-builder
6. Genera el launcher .bat
7. Compila el .iss con Inno Setup → .exe final

Requisitos para ejecutar este script:
- Windows 10/11
- Node.js + npm instalados
- Inno Setup 6.x instalado (iscc.exe en PATH)
- Conexión a internet (para descargas)

Ejecutar: python installer/build_installer.py
Salida: dist/Astra-Setup-v1.0.0.exe (~300MB)
"""
from __future__ import annotations

import os
import sys
import shutil
import zipfile
import subprocess
import urllib.request
from pathlib import Path

# === CONFIGURACIÓN ===
ASTRA_ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = ASTRA_ROOT / "dist"


# Python embebido
PYTHON_VERSION = "3.11.9"
PYTHON_EMBED_URL = f"https://www.python.org/ftp/python/{PYTHON_VERSION}/python-{PYTHON_VERSION}-embed-amd64.zip"
PYTHON_EMBED_DIR = DIST_DIR / "python-embedded"

# llama.cpp (usar releases pre-compilados de GitHub)
LLAMA_CPP_RELEASE = "b4498"
LLAMA_CPP_URL = f"https://github.com/ggerganov/llama.cpp/releases/download/{LLAMA_CPP_RELEASE}/llama-{LLAMA_CPP_RELEASE}-bin-win-avx2-x64.zip"
LLAMA_CPP_DIR = DIST_DIR / "llama-cpp"

# Electron
ELECTRON_DIR = DIST_DIR / "electron"

# Get-pip
GET_PIP_URL = "https://bootstrap.pypa.io/get-pip.py"


def print_header(msg: str):
    """Imprime un encabezado formateado."""
    print()
    print("=" * 60)
    print(f"  {msg}")
    print("=" * 60)


def print_step(step: int, total: int, msg: str):
    """Imprime un paso del proceso."""
    print(f"\n  [{step}/{total}] {msg}")


def download_file(url: str, target: Path, description: str = ""):
    """Descarga un archivo con progreso básico."""
    desc = description or target.name
    print(f"    Descargando {desc}...")
    print(f"    URL: {url}")

    try:
        def _reporthook(blocknum, blocksize, totalsize):
            if totalsize > 0:
                percent = min(100, blocknum * blocksize * 100 // totalsize)
                mb_done = (blocknum * blocksize) / (1024 * 1024)
                mb_total = totalsize / (1024 * 1024)
                print(f"\r    [{percent:3d}%] {mb_done:.1f}/{mb_total:.1f} MB", end="", flush=True)

        target.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(url, str(target), reporthook=_reporthook)
        print(f"\n    ✅ Descargado: {target.name} ({target.stat().st_size/(1024*1024):.1f} MB)")
        return True
    except Exception as e:
        print(f"\n    ❌ Error descargando: {e}")
        return False


def run_command(cmd: list[str], cwd: Path = None, description: str = "") -> bool:
    """Ejecuta un comando y muestra el resultado."""
    if description:
        print(f"    {description}")
    print(f"    $ {' '.join(cmd[:5])}{'...' if len(cmd) > 5 else ''}")

    try:
        result = subprocess.run(
            cmd, cwd=str(cwd) if cwd else None,
            capture_output=True, text=True, timeout=300
        )
        if result.returncode != 0:
            print(f"    ❌ Error (código {result.returncode})")
            if result.stderr:
                print(f"    {result.stderr[:500]}")
            return False
        return True
    except subprocess.TimeoutExpired:
        print("    ❌ Timeout (>5 min)")
        return False
    except FileNotFoundError:
        print(f"    ❌ Comando no encontrado: {cmd[0]}")
        return False


# =================================================================
# PASO 1: PREPARAR DIRECTORIO DIST
# =================================================================

def step_prepare_dist():
    """Limpia y prepara el directorio dist/."""
    print_step(1, 7, "Preparando directorio de distribución...")

    # Limpiar dist anterior (excepto descargas cacheadas)
    if DIST_DIR.exists():
        for item in DIST_DIR.iterdir():
            if item.name.endswith(".zip"):
                continue  # Mantener ZIPs descargados como cache
            if item.is_dir():
                shutil.rmtree(item, ignore_errors=True)
            else:
                item.unlink(missing_ok=True)

    DIST_DIR.mkdir(parents=True, exist_ok=True)
    PYTHON_EMBED_DIR.mkdir(parents=True, exist_ok=True)
    LLAMA_CPP_DIR.mkdir(parents=True, exist_ok=True)
    ELECTRON_DIR.mkdir(parents=True, exist_ok=True)

    print("    ✅ Directorio dist/ preparado")
    return True


# =================================================================
# PASO 2: DESCARGAR PYTHON EMBEBIDO
# =================================================================

def step_download_python():
    """Descarga y configura Python embebido."""
    print_step(2, 7, "Descargando Python embebido...")

    zip_path = DIST_DIR / f"python-{PYTHON_VERSION}-embed.zip"

    # Descargar si no está en cache
    if not zip_path.exists():
        if not download_file(PYTHON_EMBED_URL, zip_path, f"Python {PYTHON_VERSION} embebido"):
            return False

    # Extraer
    print("    Extrayendo Python embebido...")
    if PYTHON_EMBED_DIR.exists():
        shutil.rmtree(PYTHON_EMBED_DIR)
    PYTHON_EMBED_DIR.mkdir(parents=True)

    with zipfile.ZipFile(zip_path, 'r') as zf:
        zf.extractall(PYTHON_EMBED_DIR)

    # Habilitar pip: editar python311._pth para agregar site-packages
    pth_files = list(PYTHON_EMBED_DIR.glob("python*._pth"))
    if pth_files:
        pth_file = pth_files[0]
        content = pth_file.read_text()
        # Descomentar "import site"
        content = content.replace("#import site", "import site")
        # Agregar paths necesarios
        if "Lib\\site-packages" not in content:
            content += "\nLib\\site-packages\n"
        content += "..\n..\\src\n..\\installer\n"
        pth_file.write_text(content)
        print(f"    ✅ Configurado {pth_file.name} para pip y paths de Astra")

    # Instalar pip
    print("    Instalando pip...")
    get_pip_path = DIST_DIR / "get-pip.py"
    if not get_pip_path.exists():
        download_file(GET_PIP_URL, get_pip_path, "get-pip.py")

    python_exe = PYTHON_EMBED_DIR / "python.exe"
    if not python_exe.exists():
        print("    ❌ python.exe no encontrado en Python embebido")
        return False

    success = run_command(
        [str(python_exe), str(get_pip_path), "--no-warn-script-location"],
        description="Instalando pip en Python embebido..."
    )

    if success:
        print("    ✅ Python embebido listo con pip")
    return success


# =================================================================
# PASO 3: INSTALAR DEPENDENCIAS
# =================================================================

def step_install_dependencies():
    """Instala las dependencias de Astra en Python embebido."""
    print_step(3, 7, "Instalando dependencias de Astra...")

    python_exe = PYTHON_EMBED_DIR / "python.exe"
    requirements = ASTRA_ROOT / "requirements.txt"

    if not requirements.exists():
        print("    ⚠️ requirements.txt no encontrado, saltando...")
        return True

    success = run_command(
        [str(python_exe), "-m", "pip", "install",
         "--no-warn-script-location", "--no-cache-dir",
         "-r", str(requirements)],
        description="pip install -r requirements.txt"
    )

    # Instalar httpx (esencial para la comunicación con llama.cpp)
    if success:
        run_command(
            [str(python_exe), "-m", "pip", "install",
             "--no-warn-script-location", "httpx>=0.27"],
            description="Asegurando httpx..."
        )

    if success:
        print("    ✅ Dependencias instaladas")
    return success


# =================================================================
# PASO 4: DESCARGAR LLAMA.CPP
# =================================================================

def step_download_llama_cpp():
    """Descarga llama-server.exe pre-compilado."""
    print_step(4, 7, "Descargando llama.cpp server...")

    zip_path = DIST_DIR / f"llama-cpp-{LLAMA_CPP_RELEASE}.zip"

    # Si ya tenemos llama-server.exe en el proyecto, copiar
    local_server = ASTRA_ROOT / "llama-cpp" / "llama-server.exe"
    if local_server.exists():
        print("    Usando llama-server.exe local existente...")
        shutil.copy2(local_server, LLAMA_CPP_DIR / "llama-server.exe")
        # Copiar DLLs si existen
        for dll in (ASTRA_ROOT / "llama-cpp").glob("*.dll"):
            shutil.copy2(dll, LLAMA_CPP_DIR / dll.name)
        print("    ✅ llama-server.exe copiado desde proyecto local")
        return True

    # Descargar de GitHub releases
    if not zip_path.exists():
        if not download_file(LLAMA_CPP_URL, zip_path, "llama.cpp binaries"):
            print("    ⚠️ No se pudo descargar. Puedes colocar llama-server.exe manualmente en dist/llama-cpp/")
            return False

    # Extraer solo lo necesario
    print("    Extrayendo llama-server.exe...")
    with zipfile.ZipFile(zip_path, 'r') as zf:
        for member in zf.namelist():
            basename = Path(member).name.lower()
            if basename in ("llama-server.exe", "llama-cli.exe") or basename.endswith(".dll"):
                zf.extract(member, DIST_DIR / "llama-cpp-temp")

    # Mover archivos al directorio final
    temp_dir = DIST_DIR / "llama-cpp-temp"
    if temp_dir.exists():
        for f in temp_dir.rglob("*"):
            if f.is_file():
                dest = LLAMA_CPP_DIR / f.name
                shutil.copy2(f, dest)
        shutil.rmtree(temp_dir, ignore_errors=True)

    if (LLAMA_CPP_DIR / "llama-server.exe").exists():
        print("    ✅ llama-server.exe listo")
        return True
    else:
        print("    ❌ llama-server.exe no encontrado después de extraer")
        return False


# =================================================================
# PASO 5: EMPAQUETAR ELECTRON
# =================================================================

def step_build_electron():
    """Empaqueta la app Electron con electron-builder."""
    print_step(5, 7, "Empaquetando aplicación Electron...")

    desktop_dir = ASTRA_ROOT / "desktop"

    # Verificar que npm esté disponible
    if not shutil.which("npm"):
        print("    ❌ npm no encontrado en PATH. Instala Node.js primero.")
        return False

    # Instalar dependencias de Electron
    print("    Instalando dependencias de Electron...")
    success = run_command(
        ["npm", "install", "--production=false"],
        cwd=desktop_dir,
        description="npm install"
    )
    if not success:
        return False

    # Build con electron-builder (modo directory para copiar directamente)
    print("    Empaquetando con electron-builder...")
    success = run_command(
        ["npx", "electron-builder", "--win", "--dir",
         "--config.directories.output=" + str(ELECTRON_DIR)],
        cwd=desktop_dir,
        description="electron-builder --win --dir"
    )

    if not success:
        # Fallback: copiar archivos necesarios manualmente
        print("    ⚠️ electron-builder falló. Usando empaquetado manual...")
        return _manual_electron_package(desktop_dir)

    print("    ✅ Electron empaquetado")
    return True


def _manual_electron_package(desktop_dir: Path) -> bool:
    """Empaquetado manual si electron-builder no funciona."""
    try:
        # Copiar node_modules/electron/dist como base
        electron_dist = desktop_dir / "node_modules" / "electron" / "dist"
        if electron_dist.exists():
            shutil.copytree(electron_dist, ELECTRON_DIR / "electron-dist",
                           dirs_exist_ok=True)

        # Copiar código de la app
        app_dir = ELECTRON_DIR / "resources" / "app"
        app_dir.mkdir(parents=True, exist_ok=True)

        # Copiar archivos esenciales
        for item in ["electron", "package.json", "index.html", "src"]:
            src = desktop_dir / item
            dst = app_dir / item
            if src.is_dir():
                shutil.copytree(src, dst, dirs_exist_ok=True)
            elif src.is_file():
                shutil.copy2(src, dst)

        print("    ✅ Empaquetado manual completado")
        return True
    except Exception as e:
        print(f"    ❌ Error en empaquetado manual: {e}")
        return False


# =================================================================
# PASO 6: GENERAR LAUNCHER
# =================================================================

def step_create_launcher():
    """Crea el script launcher que arranca todo."""
    print_step(6, 7, "Creando launcher...")

    launcher_content = '''@echo off
REM ============================================================
REM   ASTRA — Launcher
REM   Inicia el backend Python + llama-server + Electron UI
REM ============================================================
setlocal
set "ASTRA_DIR=%~dp0"
set "PYTHON=%ASTRA_DIR%python\\python.exe"
set "LLAMA_SERVER=%ASTRA_DIR%llama-cpp\\llama-server.exe"

REM Verificar primera ejecución
if exist "%ASTRA_DIR%config\\.needs_setup" (
    echo [Astra] Primera ejecucion detectada. Iniciando setup...
    "%PYTHON%" -m installer.first_run
    del "%ASTRA_DIR%config\\.needs_setup" 2>nul
)

REM Verificar si llama-server ya está corriendo
tasklist /FI "IMAGENAME eq llama-server.exe" 2>NUL | find /I "llama-server.exe" >NUL
if %ERRORLEVEL% NEQ 0 (
    REM No está corriendo — iniciarlo con el modelo configurado
    echo [Astra] Iniciando llama-server...
    "%PYTHON%" -c "from installer.model_manager import get_model_manager; m=get_model_manager(); m.start_server()"
)

REM Iniciar backend Python
echo [Astra] Iniciando backend...
start /B "" "%PYTHON%" "%ASTRA_DIR%web\\servidor.py"

REM Esperar 2 segundos para que arranque
timeout /t 2 /nobreak >nul

REM Iniciar Electron
echo [Astra] Iniciando interfaz...
if exist "%ASTRA_DIR%Astra.exe" (
    start "" "%ASTRA_DIR%Astra.exe"
) else (
    REM Fallback: abrir en navegador
    start http://localhost:3000
)

endlocal
'''

    launcher_path = DIST_DIR / "Astra-Launcher.bat"
    launcher_path.write_text(launcher_content, encoding="utf-8")
    print(f"    ✅ Launcher creado: {launcher_path.name}")
    return True


# =================================================================
# PASO 7: COMPILAR CON INNO SETUP
# =================================================================

def step_compile_installer():
    """Compila el .iss con Inno Setup Compiler."""
    print_step(7, 7, "Compilando instalador con Inno Setup...")

    iss_file = ASTRA_ROOT / "installer" / "astra_installer.iss"

    if not iss_file.exists():
        print(f"    ❌ No se encontró {iss_file}")
        return False

    # Buscar iscc.exe
    iscc_paths = [
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
    ]

    # También buscar en PATH
    iscc_in_path = shutil.which("iscc") or shutil.which("ISCC")
    if iscc_in_path:
        iscc_paths.insert(0, iscc_in_path)

    iscc_exe = None
    for path in iscc_paths:
        if Path(path).exists():
            iscc_exe = path
            break

    if not iscc_exe:
        print("    ❌ Inno Setup Compiler (ISCC.exe) no encontrado.")
        print("    Instálalo desde: https://jrsoftware.org/isdl.php")
        print(f"    Luego ejecuta manualmente: iscc.exe \"{iss_file}\"")
        return False

    # Compilar
    success = run_command(
        [iscc_exe, str(iss_file)],
        cwd=ASTRA_ROOT,
        description=f"Compilando {iss_file.name}..."
    )

    if success:
        # Verificar que se generó el .exe
        output_exe = DIST_DIR / "Astra-Setup-v1.0.0.exe"
        if output_exe.exists():
            size_mb = output_exe.stat().st_size / (1024 * 1024)
            print(f"    ✅ Instalador generado: {output_exe.name} ({size_mb:.0f} MB)")
        else:
            print("    ✅ Compilación exitosa (verificar dist/ para el .exe)")
    else:
        print("    ❌ Error al compilar. Revisa los errores de Inno Setup.")

    return success


# =================================================================
# MAIN — EJECUCIÓN COMPLETA
# =================================================================

def build_all():
    """Ejecuta todos los pasos del build."""
    print_header("ASTRA — Build del Instalador")
    print(f"  Directorio raíz: {ASTRA_ROOT}")
    print(f"  Directorio dist: {DIST_DIR}")
    print(f"  Python embebido: {PYTHON_VERSION}")
    print(f"  llama.cpp: release {LLAMA_CPP_RELEASE}")

    steps = [
        ("Preparar directorio", step_prepare_dist),
        ("Descargar Python embebido", step_download_python),
        ("Instalar dependencias", step_install_dependencies),
        ("Descargar llama.cpp", step_download_llama_cpp),
        ("Empaquetar Electron", step_build_electron),
        ("Crear launcher", step_create_launcher),
        ("Compilar instalador", step_compile_installer),
    ]

    results = []
    for name, step_fn in steps:
        try:
            success = step_fn()
            results.append((name, success))
            if not success:
                print(f"\n  ⚠️ Paso '{name}' falló. Continuando con los siguientes...")
        except Exception as e:
            print(f"\n  ❌ Error en '{name}': {e}")
            results.append((name, False))

    # Resumen
    print_header("Resumen del Build")
    all_ok = True
    for name, success in results:
        icon = "✅" if success else "❌"
        print(f"  {icon} {name}")
        if not success:
            all_ok = False

    if all_ok:
        print(f"\n  🎉 ¡Build completo! Instalador en: dist/Astra-Setup-v1.0.0.exe")
    else:
        print(f"\n  ⚠️ Build parcial. Revisa los errores arriba.")
        print(f"  Los componentes exitosos están en: {DIST_DIR}/")

    return all_ok


def build_without_inno():
    """Build sin Inno Setup (genera dist/ pero no el .exe final)."""
    print_header("ASTRA — Build (sin Inno Setup)")
    print("  Generando componentes en dist/ para empaquetado manual...")

    steps = [
        step_prepare_dist,
        step_download_python,
        step_install_dependencies,
        step_download_llama_cpp,
        step_build_electron,
        step_create_launcher,
    ]

    for step_fn in steps:
        try:
            step_fn()
        except Exception as e:
            print(f"  ⚠️ Error: {e}")

    print(f"\n  ✅ Componentes listos en: {DIST_DIR}/")
    print(f"  Para generar el .exe, instala Inno Setup y ejecuta:")
    print(f"  iscc.exe installer/astra_installer.iss")


# === CLI ===
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="ASTRA — Build del instalador .exe")
    parser.add_argument("--no-inno", action="store_true",
                        help="Generar dist/ sin compilar con Inno Setup")
    parser.add_argument("--step", type=int, choices=range(1, 8),
                        help="Ejecutar solo un paso específico (1-7)")
    parser.add_argument("--clean", action="store_true",
                        help="Limpiar dist/ completamente antes de empezar")

    args = parser.parse_args()

    if args.clean:
        print("Limpiando dist/...")
        if DIST_DIR.exists():
            shutil.rmtree(DIST_DIR)
        print("✅ Limpio")

    if args.step:
        step_map = {
            1: step_prepare_dist,
            2: step_download_python,
            3: step_install_dependencies,
            4: step_download_llama_cpp,
            5: step_build_electron,
            6: step_create_launcher,
            7: step_compile_installer,
        }
        step_fn = step_map[args.step]
        step_fn()
    elif args.no_inno:
        build_without_inno()
    else:
        build_all()
