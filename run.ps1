$ErrorActionPreference = 'Stop'
$taskPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $taskPython)) {
    Write-Error 'Crea el entorno con: py -3.12 -m venv .venv; .\.venv\Scripts\python -m pip install -e .'
    exit 1
}
& $taskPython -m marksfuncs_ui @args
exit $LASTEXITCODE
