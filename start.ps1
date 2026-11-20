<#
.SYNOPSIS
    Inicia o Meeting & Video Intelligence em portas/URLs dedicadas (sem conflitar com 8000/5173/3000).
.EXAMPLE
    .\start.ps1           # Modo Single-Server em http://mvi.localhost:8185 (recomendado)
    .\start.ps1 -Dev      # Modo Dev: Frontend em http://mvi.localhost:5185 + API em :8185
    .\start.ps1 -Rebuild  # Recompila o frontend antes de subir no modo Single-Server
#>
param(
    [switch]$Dev,
    [switch]$Rebuild,
    [int]$ApiPort = 8185,
    [int]$UiPort = 5185
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    Write-Error "Ambiente virtual .venv nao encontrado em $Python. Execute: python -m venv .venv && .venv\Scripts\pip.exe install -r backend\requirements.txt"
    exit 1
}

if ($Dev) {
    Write-Host "Iniciando Meeting & Video Intelligence (Modo Dev)..." -ForegroundColor Cyan
    Write-Host "  Frontend: http://mvi.localhost:$UiPort  (ou http://localhost:$UiPort)" -ForegroundColor Green
    Write-Host "  Backend:  http://mvi.localhost:$ApiPort (Swagger: http://mvi.localhost:$ApiPort/docs)" -ForegroundColor Green

    $backendJob = Start-Process -FilePath $Python `
        -ArgumentList "-m", "uvicorn", "app.main:app", "--app-dir", "backend", "--reload", "--host", "127.0.0.1", "--port", "$ApiPort" `
        -WorkingDirectory $Root -PassThru -NoNewWindow

    try {
        Push-Location (Join-Path $Root "frontend")
        $env:VITE_API_TARGET = "http://127.0.0.1:$ApiPort"
        & npm.cmd run dev -- --port $UiPort
    }
    finally {
        Pop-Location
        if ($backendJob -and -not $backendJob.HasExited) {
            Stop-Process -Id $backendJob.Id -Force -ErrorAction SilentlyContinue
        }
    }
}
else {
    $distIndex = Join-Path $Root "frontend\dist\index.html"
    if ($Rebuild -or -not (Test-Path $distIndex)) {
        Write-Host "Compilando frontend (frontend/dist)..." -ForegroundColor Cyan
        Push-Location (Join-Path $Root "frontend")
        try {
            & npm.cmd run build
        }
        finally {
            Pop-Location
        }
    }

    Write-Host "Iniciando Meeting & Video Intelligence (Single-Server)..." -ForegroundColor Cyan
    Write-Host "  App URL:  http://mvi.localhost:$ApiPort (ou http://localhost:$ApiPort)" -ForegroundColor Green
    Write-Host "  API Docs: http://mvi.localhost:$ApiPort/docs" -ForegroundColor Green
    & $Python -m uvicorn app.main:app --app-dir (Join-Path $Root "backend") --host 127.0.0.1 --port $ApiPort
}
