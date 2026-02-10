# Stage 3 Integration Test Orchestration Script (Windows)
# Usage: .\scripts\test-integration.ps1
#
# Automates: docker-compose up -> wait for health -> seed DB -> run tests -> report -> teardown

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$ComposeDir = Join-Path $ProjectRoot "production"
$TestExitCode = 0

function Write-Banner($message) {
    Write-Host ""
    Write-Host "=" * 60 -ForegroundColor Cyan
    Write-Host " $message" -ForegroundColor Cyan
    Write-Host "=" * 60 -ForegroundColor Cyan
    Write-Host ""
}

function Cleanup {
    Write-Banner "TEARDOWN: Stopping docker-compose stack"
    Push-Location $ComposeDir
    docker-compose down -v 2>&1 | Out-Null
    Pop-Location
}

# Trap to ensure cleanup on exit
trap { Cleanup } EXIT

try {
    # 1. Start the docker-compose stack
    Write-Banner "STEP 1: Starting docker-compose stack"
    Push-Location $ComposeDir
    docker-compose up -d 2>&1
    Pop-Location

    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: docker-compose up failed" -ForegroundColor Red
        exit 1
    }

    # 2. Wait for services to be healthy
    Write-Banner "STEP 2: Waiting for services to be healthy"
    python "$ProjectRoot\scripts\wait-for-healthy.py" --timeout 120 --interval 5

    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Services did not become healthy in time" -ForegroundColor Red
        exit 1
    }

    # 3. Apply database schema
    Write-Banner "STEP 3: Applying database schema"
    docker exec -i production-postgres-1 psql -U fte -d fte_crm < "$ComposeDir\database\schema.sql"

    if ($LASTEXITCODE -ne 0) {
        Write-Host "WARNING: Schema application had issues (may already exist)" -ForegroundColor Yellow
    }

    # 4. Run database seed
    Write-Banner "STEP 4: Seeding database"
    docker exec production-api-1 python -c "from production.database.seed import seed_database; import asyncio; asyncio.run(seed_database())" 2>&1

    # 5. Run unit tests (no Docker needed)
    Write-Banner "STEP 5: Running unit tests"
    Push-Location $ProjectRoot
    python -m pytest tests/ production/tests/test_agent.py production/tests/test_channels.py production/tests/test_transition.py -v --tb=short 2>&1
    $UnitExitCode = $LASTEXITCODE
    Pop-Location

    if ($UnitExitCode -ne 0) {
        Write-Host "WARNING: Some unit tests failed (exit code: $UnitExitCode)" -ForegroundColor Yellow
        $TestExitCode = $UnitExitCode
    } else {
        Write-Host "Unit tests: ALL PASSED" -ForegroundColor Green
    }

    # 6. Run database integration tests
    Write-Banner "STEP 6: Running database integration tests"
    Push-Location $ProjectRoot
    python -m pytest production/tests/test_database.py -v --tb=short 2>&1
    $DbExitCode = $LASTEXITCODE
    Pop-Location

    if ($DbExitCode -ne 0) {
        Write-Host "WARNING: Some database tests failed (exit code: $DbExitCode)" -ForegroundColor Yellow
        $TestExitCode = $DbExitCode
    } else {
        Write-Host "Database tests: ALL PASSED" -ForegroundColor Green
    }

    # 7. Run E2E tests
    Write-Banner "STEP 7: Running end-to-end tests"
    Push-Location $ProjectRoot
    python -m pytest production/tests/test_e2e.py -v --tb=short 2>&1
    $E2eExitCode = $LASTEXITCODE
    Pop-Location

    if ($E2eExitCode -ne 0) {
        Write-Host "WARNING: Some E2E tests failed (exit code: $E2eExitCode)" -ForegroundColor Yellow
        $TestExitCode = $E2eExitCode
    } else {
        Write-Host "E2E tests: ALL PASSED" -ForegroundColor Green
    }

    # 8. Summary
    Write-Banner "TEST SUMMARY"
    Write-Host "Unit tests:     $(if ($UnitExitCode -eq 0) { 'PASS' } else { 'FAIL' })" -ForegroundColor $(if ($UnitExitCode -eq 0) { 'Green' } else { 'Red' })
    Write-Host "Database tests: $(if ($DbExitCode -eq 0) { 'PASS' } else { 'FAIL' })" -ForegroundColor $(if ($DbExitCode -eq 0) { 'Green' } else { 'Red' })
    Write-Host "E2E tests:      $(if ($E2eExitCode -eq 0) { 'PASS' } else { 'FAIL' })" -ForegroundColor $(if ($E2eExitCode -eq 0) { 'Green' } else { 'Red' })
    Write-Host ""

} finally {
    Cleanup
}

exit $TestExitCode
