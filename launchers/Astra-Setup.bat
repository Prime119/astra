@echo off
REM ============================================================
REM   ASTRA - Instalador RESIDENTE (copia a esta PC)
REM   Astra vivira en segundo plano, tipo asistente del sistema.
REM   Requiere permisos para escribir en la PC.
REM ============================================================
setlocal
echo [Astra] Modo RESIDENTE.
echo  - El perfil del usuario se guardara en: %USERPROFILE%\.astra
echo  - La base del programa permanece SIN modificarse (solo lectura).
echo.
echo (Fase 1+) Aqui se configurara el arranque con Windows y el servicio en segundo plano.
echo Por ahora, modo desarrollo:
cd /d "%~dp0.."
python -m astra.main --status
endlocal
