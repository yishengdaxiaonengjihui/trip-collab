# One-shot demo launcher: FastAPI (serves frontend/dist + /api) + Cloudflare quick tunnel.
# Usage: right-click -> "Run with PowerShell".
# If you get "Access is denied" reading .pydeps, run it as Administrator instead.
#
# The public URL is printed by cloudflared and CHANGES ON EVERY RESTART.
# Keep this window open for the whole presentation; closing it kills the tunnel.

$ErrorActionPreference = 'Stop'
$repo        = $PSScriptRoot
$python      = 'D:\apps\miniconda3\python.exe'
$cloudflared = 'D:\dsh\trip project\.tools\cloudflared-windows-amd64.exe'
$port        = 8000

if (-not (Test-Path "$repo\frontend\dist\index.html")) {
    Write-Host '[X] frontend/dist is missing. Run "npm run build" in frontend/ first.' -ForegroundColor Red
    exit 1
}
if (-not (Test-Path $cloudflared)) {
    Write-Host "[X] cloudflared not found at $cloudflared" -ForegroundColor Red
    exit 1
}

$env:PYTHONPATH = "$repo\.pydeps"

# Start backend in its own window (skip if something already answers on the port).
$alreadyUp = $false
try {
    $c = New-Object Net.Sockets.TcpClient
    $c.Connect('127.0.0.1', $port)
    $alreadyUp = $c.Connected
    $c.Close()
} catch { $alreadyUp = $false }

if ($alreadyUp) {
    Write-Host "[i] Port $port already serving - reusing the running backend." -ForegroundColor Yellow
} else {
    Start-Process -FilePath $python `
        -ArgumentList '-m', 'uvicorn', 'backend.app.main:app', '--host', '127.0.0.1', '--port', "$port" `
        -WorkingDirectory $repo -WindowStyle Minimized
    Write-Host "[+] Backend starting on 127.0.0.1:$port ..." -ForegroundColor Green
    Start-Sleep -Seconds 6
}

# First run only: seed the demo trip (seed_demo.py creates a NEW trip every call).
if (-not (Test-Path "$repo\backend\data\trip.db")) {
    Write-Host '[+] First run: seeding demo data ...' -ForegroundColor Yellow
    & $python "$repo\frontend\seed_demo.py"
}

Write-Host ''
Write-Host '=== Public URL appears below - share it with classmates/teacher ===' -ForegroundColor Cyan
Write-Host ''
& $cloudflared tunnel --url "http://127.0.0.1:$port" --no-autoupdate
