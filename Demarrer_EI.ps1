Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "   Lancement de EI - Assistant Vocal & HUD 3D" -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host ""

$pythonCmd = $null
$pythonArgs = @()

if (Test-Path ".venv\Scripts\python.exe") {
    $pythonCmd = ".venv\Scripts\python.exe"
} elseif (Test-Path "venv\Scripts\python.exe") {
    $pythonCmd = "venv\Scripts\python.exe"
} else {
    try {
        $null = & python -c "import websockets" 2>$null
        if ($LASTEXITCODE -eq 0) {
            $pythonCmd = "python"
        }
    } catch {}

    if (-not $pythonCmd) {
        try {
            $null = & py -3.13 -c "import websockets" 2>$null
            if ($LASTEXITCODE -eq 0) {
                $pythonCmd = "py"
                $pythonArgs = @("-3.13")
            }
        } catch {}
    }

    if (-not $pythonCmd) {
        $cmd = Get-Command python -ErrorAction SilentlyContinue
        if ($cmd) {
            $pythonCmd = $cmd.Source
        } else {
            $py = Get-Command py -ErrorAction SilentlyContinue
            if ($py) {
                $pythonCmd = "py"
                $pythonArgs = @("-3")
            }
        }
    }
}

if (-not $pythonCmd) {
    Write-Host "[ERREUR] Aucun interpreteur Python trouve." -ForegroundColor Red
    Read-Host "Appuyez sur Entrée pour quitter..."
    exit 1
}

Write-Host "Démarrage du système avec $pythonCmd $pythonArgs..." -ForegroundColor Green
& $pythonCmd $pythonArgs run.py
