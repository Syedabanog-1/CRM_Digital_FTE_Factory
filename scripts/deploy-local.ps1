# deploy-local.ps1
# Automated local Kubernetes deployment for CRM Digital FTE Factory
# Prerequisites: minikube, kubectl, kustomize (bundled with kubectl)

param(
    [int]$Cpus = 4,
    [int]$Memory = 4096,
    [string]$Driver = "docker",
    [switch]$SkipMinikubeStart,
    [switch]$SkipSchemaApply
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Namespace = "fte-local"

function Write-Step {
    param([string]$Message)
    Write-Host "`n==> $Message" -ForegroundColor Cyan
}

function Wait-ForPod {
    param(
        [string]$Label,
        [int]$TimeoutSeconds = 180
    )
    Write-Host "    Waiting for pod with label app=$Label to be Ready (timeout: ${TimeoutSeconds}s)..."
    $elapsed = 0
    while ($elapsed -lt $TimeoutSeconds) {
        $status = kubectl get pods -n $Namespace -l "app=$Label" -o jsonpath="{.items[0].status.conditions[?(@.type=='Ready')].status}" 2>$null
        if ($status -eq "True") {
            Write-Host "    Pod $Label is Ready." -ForegroundColor Green
            return $true
        }
        Start-Sleep -Seconds 5
        $elapsed += 5
    }
    Write-Host "    WARNING: Pod $Label did not become Ready within ${TimeoutSeconds}s." -ForegroundColor Yellow
    return $false
}

# ------------------------------------------------------------------
# Step 1: Start Minikube
# ------------------------------------------------------------------
if (-not $SkipMinikubeStart) {
    Write-Step "Starting Minikube (cpus=$Cpus, memory=${Memory}MB, driver=$Driver)"
    minikube start --cpus=$Cpus --memory=$Memory --driver=$Driver
} else {
    Write-Step "Skipping Minikube start (flag set)"
}

# ------------------------------------------------------------------
# Step 2: Set kubectl context
# ------------------------------------------------------------------
Write-Step "Setting kubectl context to minikube"
kubectl config use-context minikube

# ------------------------------------------------------------------
# Step 3: Enable metrics-server addon
# ------------------------------------------------------------------
Write-Step "Enabling metrics-server addon"
minikube addons enable metrics-server

# ------------------------------------------------------------------
# Step 4: Create namespace (if not exists)
# ------------------------------------------------------------------
Write-Step "Ensuring namespace $Namespace exists"
$nsExists = kubectl get namespace $Namespace 2>$null
if (-not $nsExists) {
    kubectl create namespace $Namespace
    Write-Host "    Namespace $Namespace created." -ForegroundColor Green
} else {
    Write-Host "    Namespace $Namespace already exists." -ForegroundColor Green
}

# ------------------------------------------------------------------
# Step 5: Build and apply Kustomize overlay
# ------------------------------------------------------------------
Write-Step "Applying Kustomize overlay from k8s/overlays/local"
kubectl kustomize "$ProjectRoot\k8s\overlays\local" --load-restrictor LoadRestrictionsNone | kubectl apply -f -

# ------------------------------------------------------------------
# Step 6: Wait for infrastructure pods (postgres, kafka)
# ------------------------------------------------------------------
Write-Step "Waiting for infrastructure pods"
$pgReady = Wait-ForPod -Label "postgres" -TimeoutSeconds 120
$kafkaReady = Wait-ForPod -Label "kafka" -TimeoutSeconds 120

if (-not $pgReady) {
    Write-Host "ERROR: PostgreSQL pod did not start. Check logs with: kubectl logs -n $Namespace -l app=postgres" -ForegroundColor Red
    exit 1
}

# ------------------------------------------------------------------
# Step 7: Apply database schema
# ------------------------------------------------------------------
if (-not $SkipSchemaApply) {
    Write-Step "Applying database schema"
    $pgPod = kubectl get pods -n $Namespace -l "app=postgres" -o jsonpath="{.items[0].metadata.name}"

    # Copy schema file into the pod
    kubectl cp "$ProjectRoot\production\database\schema.sql" "${Namespace}/${pgPod}:/tmp/schema.sql"

    # Execute schema
    kubectl exec -n $Namespace $pgPod -- psql -U fte -d fte_crm -f /tmp/schema.sql

    Write-Host "    Database schema applied." -ForegroundColor Green
} else {
    Write-Step "Skipping schema apply (flag set)"
}

# ------------------------------------------------------------------
# Step 8: Wait for application pods (api, worker)
# ------------------------------------------------------------------
Write-Step "Waiting for application pods"
Wait-ForPod -Label "fte-api" -TimeoutSeconds 180
Wait-ForPod -Label "fte-worker" -TimeoutSeconds 180

# ------------------------------------------------------------------
# Step 9: Wait for monitoring pods (prometheus, grafana)
# ------------------------------------------------------------------
Write-Step "Waiting for monitoring pods"
Wait-ForPod -Label "prometheus" -TimeoutSeconds 120
Wait-ForPod -Label "grafana" -TimeoutSeconds 120

# ------------------------------------------------------------------
# Step 10: Print access information
# ------------------------------------------------------------------
Write-Step "Deployment complete! Getting service URLs"

$minikubeIp = minikube ip

Write-Host ""
Write-Host "=============================================" -ForegroundColor Green
Write-Host " Local Kubernetes Deployment Ready" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Green
Write-Host ""
Write-Host "  API:         http://${minikubeIp}:30080" -ForegroundColor White
Write-Host "  API Docs:    http://${minikubeIp}:30080/docs" -ForegroundColor White
Write-Host "  Prometheus:  http://${minikubeIp}:30090" -ForegroundColor White
Write-Host "  Grafana:     http://${minikubeIp}:30030  (admin/admin)" -ForegroundColor White
Write-Host ""
Write-Host "  Namespace:   $Namespace" -ForegroundColor Gray
Write-Host ""
Write-Host "Useful commands:" -ForegroundColor Gray
Write-Host "  kubectl get pods -n $Namespace" -ForegroundColor Gray
Write-Host "  kubectl logs -n $Namespace -l app=fte-api --tail=50" -ForegroundColor Gray
Write-Host "  kubectl logs -n $Namespace -l app=fte-worker --tail=50" -ForegroundColor Gray
Write-Host ""
