@echo off
REM ============================================================
REM  ASTRA / MEC - Instalador de librerias (Windows)
REM  Doble clic para instalar todo lo que necesita el programa.
REM ============================================================
cd /d "%~dp0"
echo.
echo === Actualizando pip ===
python -m pip install --upgrade pip

echo.
echo === Librerias base del programa ===
python -m pip install -r requirements.txt

echo.
echo === Librerias de Face ID (reconocimiento del creador) ===
echo  (face_recognition usa dlib; en Windows puede tardar)
python -m pip install opencv-python numpy
python -m pip install face_recognition
if errorlevel 1 (
  echo.
  echo  ATENCION: face_recognition fallo. En Windows suele necesitar dlib precompilado.
  echo  Opcion: instala "dlib-bin" y reintenta:
  echo     python -m pip install dlib-bin
  echo     python -m pip install face_recognition
)

echo.
echo === Listo ===
echo  - Probar el nucleo:        python -m astra --status
echo  - Enrolar tu rostro:        python -m astra --enroll-face
echo  - Aprender de OSM (CFE):    python -m astra --cfe --falcon-learn
pause
