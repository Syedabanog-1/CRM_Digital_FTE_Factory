# Run all unit tests (no Docker required)
# Usage: .\scripts\run-unit-tests.ps1

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Push-Location $ProjectRoot

Write-Host "Running all unit tests..." -ForegroundColor Cyan
python -m pytest tests/ production/tests/test_agent.py production/tests/test_channels.py production/tests/test_transition.py -v

$ExitCode = $LASTEXITCODE
Pop-Location
exit $ExitCode
