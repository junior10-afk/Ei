@echo off
title EI - Installation et Configuration
cls
echo =======================================================
echo    Installation des dependances pour EI Assistant
echo =======================================================
echo.

set PYTHON_EXE=C:\Users\lemou\AppData\Local\Programs\Python\Python313\python.exe
if not exist "%PYTHON_EXE%" (
    set PYTHON_EXE=python
)

echo [1/3] Installation des modules Python...
"%PYTHON_EXE%" -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [Avertissement] Verifiez l'installation des dependances Python.
)

echo.
echo [2/3] Verification de l'environnement frontend...
cd frontend
where npm >nul 2>nul
if %errorlevel% equ 0 (
    echo Installation des modules npm...
    call npm install
    echo Compilation du HUD Vite...
    call npm run build
) else (
    echo [Info] npm non detecte, les fichiers frontend compiles existants seront utilises.
)
cd ..

echo.
echo [3/3] Creation du fichier .env si absent...
if not exist ".env" (
    if exist ".env.example" (
        copy .env.example .env
        echo Fichier .env cree a partir de .env.example. Vous pouvez y renseigner vos cles API.
    )
)

echo.
echo =======================================================
echo    Installation terminee avec succes !
echo    Lancez DEMARRER_EI.bat pour demarrer l'assistant.
echo =======================================================
pause
