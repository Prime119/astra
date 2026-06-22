@echo off
REM ============================================================
REM   ASTRA - Lanzador PORTATIL (corre desde la SSD)
REM   No instala nada en la PC. Todo (base + perfil) en la SSD.
REM ============================================================
setlocal
cd /d "%~dp0.."

REM Marca de modo portatil
set ASTRA_PORTABLE=1

REM (Fase 1+) Aqui se arrancara el runtime embebido de Python/Node de la SSD.
REM Por ahora, modo desarrollo:
echo [Astra] Iniciando en modo PORTATIL...
python -m astra.main
endlocal
