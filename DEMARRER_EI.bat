@echo off
title EI - Assistant Vocal
cls
echo =======================================================
echo    Lancement de EI - Assistant Vocal 3D
echo =======================================================
echo.
set PYTHON_CMD=
if exist ".venv\Scripts\python.exe" (
    set PYTHON_CMD=.venv\Scripts\python.exe
) else if exist "venv\Scripts\python.exe" (
    set PYTHON_CMD=venv\Scripts\python.exe
) else (
    python -c "__import__('websockets')" >nul 2>&1
    if not errorlevel 1 (
        set PYTHON_CMD=python
    ) else (
        py -3.13 -c "__import__('websockets')" >nul 2>&1
        if not errorlevel 1 (
            set PYTHON_CMD=py -3.13
        ) else (
            where python >nul 2>&1
            if not errorlevel 1 (
                set PYTHON_CMD=python
            ) else (
                set PYTHON_CMD=py -3
            )
        )
    )
)

if "%PYTHON_CMD%"=="" (
    echo [ERREUR] Aucun interpreteur Python trouve. Veuillez installer Python 3.11+.
    pause
    exit /b 1
)

echo Demarrage de EI avec : %PYTHON_CMD%
%PYTHON_CMD% run.py
if %errorlevel% neq 0 (
    echo.
    echo [Erreur] L'application s'est fermee avec le code %errorlevel%.
    pause
)
