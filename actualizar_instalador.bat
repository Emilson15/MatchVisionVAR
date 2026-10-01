@echo off
title Actualizar Instalador MatchVision VAR
cd /d "%~dp0"
echo Iniciando proceso de actualizacion del instalador...
".venv\Scripts\python.exe" actualizar_instalador.py
echo.
pause
