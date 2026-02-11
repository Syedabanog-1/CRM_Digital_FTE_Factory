# teardown-local.ps1
# Tears down the local Kubernetes deployment for CRM Digital FTE Factory

param(
    [switch]$StopMinikube,
    [switch]$DeleteMinikube
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Namespace = "fte-local"

function Write-Step {
    param([string]$Message)
    Write-Host "`n==> $Message" -ForegroundColor Cyan
}

# ------------------------------------------------------------------
# Step 1: Delete Kustomize resources
# ------------------------------------------------------------------
Write-Step "Deleting Kustomize resources from namespace $Namespace"
try {
    kubectl kustomize "$ProjectRoot\k8s\overlays\local" --load-restrictor LoadRestrictionsNone | kubectl delete --ignore-not-found -f -
    Write-Host "    Resources deleted." -ForegroundColor Green
} catch {
    Write-Host "    Warning: Some resources may not have been deleted: $_" -ForegroundColor Yellow
}

# ------------------------------------------------------------------
# Step 2: Delete namespace
# ------------------------------------------------------------------
Write-Step "Deleting namespace $Namespace"
try {
    kubectl delete namespace $Namespace --ignore-not-found
    Write-Host "    Namespace deleted." -ForegroundColor Green
} catch {
    Write-Host "    Warning: Namespace deletion failed: $_" -ForegroundColor Yellow
}

# ------------------------------------------------------------------
# Step 3: Optionally stop or delete Minikube
# ------------------------------------------------------------------
if ($DeleteMinikube) {
    Write-Step "Deleting Minikube cluster"
    minikube delete
    Write-Host "    Minikube cluster deleted." -ForegroundColor Green
} elseif ($StopMinikube) {
    Write-Step "Stopping Minikube"
    minikube stop
    Write-Host "    Minikube stopped." -ForegroundColor Green
} else {
    Write-Host "`nMinikube is still running. Use -StopMinikube or -DeleteMinikube to stop/delete it." -ForegroundColor Gray
}

Write-Host ""
Write-Host "=============================================" -ForegroundColor Green
Write-Host " Teardown Complete" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Green
Write-Host ""
