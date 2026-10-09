$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (Test-Path -LiteralPath '.venv\Scripts\python.exe') {
    & '.venv\Scripts\python.exe' -m uvicorn app.main:app --host 127.0.0.1 --port 8000
} else {
    python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
}
