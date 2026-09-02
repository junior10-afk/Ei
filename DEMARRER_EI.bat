@echo off
title EI - Assistant Vocal
cls
echo =======================================================
echo    Lancement de EI - Assistant Vocal 3D
echo =======================================================
echo.
set PYTHON_EXE=C:\Users\lemou\AppData\Local\Programs\Python\Python313\python.exe
if not exist "%PYTHON_EXE%" (
    set PYTHON_EXE=python
)
echo Demarrage de EI...
"%PYTHON_EXE%" run.py
if %errorlevel% neq 0 (
    echo.
    echo [Erreur] L'application s'est fermee avec le code %errorlevel%.
    pause
)
