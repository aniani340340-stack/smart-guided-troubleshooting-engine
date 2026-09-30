# Sets Node.js path for current session and starts Vite dev server
$env:Path = "C:\Users\anian\nodejs;" + $env:Path
Set-Location -Path "$PSScriptRoot\frontend"
Write-Host "Starting Galaxy Diagnostic Frontend on http://localhost:5173..." -ForegroundColor Cyan
npm run dev
