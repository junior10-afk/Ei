Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "   Lancement de EI - Assistant Vocal & HUD 3D" -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host ""

$pythonExe = "C:\Users\lemou\AppData\Local\Programs\Python\Python313\python.exe"

if (-not (Test-Path $pythonExe)) {
    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCmd) {
        $pythonExe = $pythonCmd.Source
    } else {
        Write-Host "[ERREUR] Python 3.13 introuvable." -ForegroundColor Red
        Read-Host "Appuyez sur Entrée pour quitter..."
        exit 1
    }
}

Write-Host "Démarrage du système avec $pythonExe..." -ForegroundColor Green
& $pythonExe run.py
