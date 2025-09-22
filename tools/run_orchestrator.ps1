Param(
    [string]$PythonExe = "python"
)

$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path "$PSScriptRoot\..\").Path
$OrchDir = Join-Path $RepoRoot "releases/current/orchestrator"

Write-Host "[orchestrator] creating venv..."
python -m venv "$OrchDir\.venv"

Write-Host "[orchestrator] installing requirements..."
& "$OrchDir\.venv\Scripts\pip.exe" install -r "$OrchDir\requirements.txt" | Write-Host

Write-Host "[orchestrator] starting..."
& "$OrchDir\.venv\Scripts\python.exe" "$OrchDir\orchestrator.py"

