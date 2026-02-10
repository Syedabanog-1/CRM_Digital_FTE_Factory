# Run Locust load test and generate report
# Usage: .\scripts\run-load-test.ps1 [--users 10] [--duration 5m]
# Requires: docker-compose stack running

param(
    [int]$Users = 10,
    [string]$Duration = "5m",
    [int]$SpawnRate = 2
)

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$ReportsDir = Join-Path $ProjectRoot "reports"

# Ensure reports directory exists
if (-not (Test-Path $ReportsDir)) {
    New-Item -ItemType Directory -Path $ReportsDir | Out-Null
}

# Check if stack is running
Write-Host "Checking if API is healthy..." -ForegroundColor Cyan
try {
    $health = Invoke-RestMethod -Uri "http://localhost:8000/health" -TimeoutSec 5
    Write-Host "API is healthy: $($health.status)" -ForegroundColor Green
} catch {
    Write-Host "ERROR: API is not running. Start with: docker-compose up -d" -ForegroundColor Red
    exit 1
}

# Run Locust
$timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$csvPrefix = Join-Path $ReportsDir "load-test-$timestamp"

Write-Host ""
Write-Host "Starting load test: $Users users, $Duration duration, spawn rate $SpawnRate/s" -ForegroundColor Cyan
Write-Host ""

Push-Location $ProjectRoot
locust -f production/tests/load_test.py `
    --host=http://localhost:8000 `
    --headless `
    --users $Users `
    --spawn-rate $SpawnRate `
    --run-time $Duration `
    --csv="$csvPrefix" `
    --html="$ReportsDir\load-test-$timestamp.html"

$ExitCode = $LASTEXITCODE
Pop-Location

# Generate markdown report
if (Test-Path "${csvPrefix}_stats.csv") {
    Write-Host ""
    Write-Host "Load test complete. Generating report..." -ForegroundColor Cyan

    $report = @"
# Load Test Report

**Date**: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
**Users**: $Users
**Duration**: $Duration
**Spawn Rate**: $SpawnRate/s

## Results

See CSV files in ``reports/`` for detailed metrics:
- ``load-test-${timestamp}_stats.csv`` - Request statistics
- ``load-test-${timestamp}_stats_history.csv`` - Time series
- ``load-test-${timestamp}_failures.csv`` - Failures
- ``load-test-${timestamp}.html`` - HTML report

## SLA Validation

| Metric | Target | Status |
|--------|--------|--------|
| p95 Latency | < 3000ms | CHECK CSV |
| Error Rate | < 1% | CHECK CSV |
| Concurrent Users | >= 10 | $Users |

"@

    $report | Out-File -FilePath "$ReportsDir\load-test-report.md" -Encoding utf8
    Write-Host "Report saved to: reports\load-test-report.md" -ForegroundColor Green
}

exit $ExitCode
