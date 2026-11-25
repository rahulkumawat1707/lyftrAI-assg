$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
$vitePath = Join-Path $projectRoot 'frontend\node_modules\vite\bin\vite.js'
if (!(Test-Path $pythonPath) -or !(Test-Path $vitePath)) {
    throw 'Install Python and frontend dependencies first. See README.md.'
}
New-Item -ItemType Directory -Force (Join-Path $projectRoot 'tmp') | Out-Null
foreach ($port in @(3000, 8000)) {
    if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) {
        throw "Port $port is already in use. Existing servers have been left running."
    }
}
Start-Process -FilePath $pythonPath -ArgumentList '-m','uvicorn','backend.app.main:app','--host','127.0.0.1','--port','8000' -WorkingDirectory $projectRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $projectRoot 'tmp\backend.log') -RedirectStandardError (Join-Path $projectRoot 'tmp\backend-error.log')
Start-Process -FilePath (Get-Command node).Source -ArgumentList "`"$vitePath`"",'--host','127.0.0.1','--port','3000','--strictPort' -WorkingDirectory (Join-Path $projectRoot 'frontend') -WindowStyle Hidden -RedirectStandardOutput (Join-Path $projectRoot 'tmp\frontend.log') -RedirectStandardError (Join-Path $projectRoot 'tmp\frontend-error.log')
Write-Host 'Frontend: http://127.0.0.1:3000'
Write-Host 'Backend:  http://127.0.0.1:8000/health'
Write-Host 'Logs: tmp/frontend.log and tmp/backend-error.log'
