# Starts Docker Desktop and the EarlyShield stack on this Windows machine.
#
# Why this exists: when Windows shuts down while Docker Desktop is running,
# Docker leaves stale socket files behind (Docker\run\sailor-ingest.sock,
# docker-secrets-engine\engine.sock). On the next start it crashes with
# "The file cannot be accessed by the system". Those folders only hold
# runtime sockets, so moving them aside (not deleting) is safe; Docker
# recreates them. Images, containers and database volumes are untouched.
#
# NEVER click "Reset to factory defaults" in that error dialog: it deletes
# every image and the database.
#
# Usage (from this folder):  powershell -ExecutionPolicy Bypass -File .\start-earlyshield.ps1

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Test-DockerEngine {
    docker info *> $null
    return $LASTEXITCODE -eq 0
}

if (-not (Test-DockerEngine)) {
    $desktop = Get-Process -Name "Docker Desktop" -ErrorAction SilentlyContinue
    if ($desktop) {
        Write-Host "Docker Desktop is running but its engine isn't (probably the stale-socket crash). Closing it..."
        Get-Process | Where-Object { $_.ProcessName -match '^(Docker Desktop|com\.docker\..*|vpnkit.*)$' } |
            Stop-Process -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 3
    }

    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    foreach ($dir in @("$env:LOCALAPPDATA\Docker\run", "$env:LOCALAPPDATA\docker-secrets-engine")) {
        if (Test-Path $dir) {
            Rename-Item $dir "$dir.stale-$stamp"
            Write-Host "Moved stale folder aside: $dir"
        }
    }

    $exe = @(
        "$env:LOCALAPPDATA\Programs\DockerDesktop\Docker Desktop.exe",
        "$env:ProgramFiles\Docker\Docker\Docker Desktop.exe"
    ) | Where-Object { Test-Path $_ } | Select-Object -First 1
    if (-not $exe) { throw "Docker Desktop.exe not found. Start Docker Desktop by hand." }

    Write-Host "Starting Docker Desktop..."
    Start-Process $exe
    $deadline = (Get-Date).AddMinutes(3)
    while (-not (Test-DockerEngine)) {
        if ((Get-Date) -gt $deadline) { throw "Docker didn't start within 3 minutes. Open Docker Desktop and check for an error." }
        Start-Sleep -Seconds 3
    }
}
Write-Host "Docker engine is up."

docker compose up -d
Write-Host "Waiting for EarlyShield to become healthy..."
$deadline = (Get-Date).AddMinutes(2)
do {
    Start-Sleep -Seconds 3
    try { $ok = (Invoke-WebRequest -UseBasicParsing -TimeoutSec 3 "http://localhost:5173/api/v1/system/health").StatusCode -eq 200 } catch { $ok = $false }
} until ($ok -or (Get-Date) -gt $deadline)

if ($ok) {
    Write-Host "EarlyShield is ready: http://localhost:5173" -ForegroundColor Green
    Start-Process "http://localhost:5173"
} else {
    Write-Host "Containers started but the app isn't answering yet. Run: docker compose ps" -ForegroundColor Yellow
}
