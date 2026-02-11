---
id: 004
title: Local Kubernetes Deployment Implementation
stage: general
date: 2026-02-11
surface: agent
model: claude-opus-4-6
feature: none
branch: 001-stage1-incubation
user: syeda
command: implement
labels: ["kubernetes", "kustomize", "minikube", "local-deployment", "monitoring"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - k8s/kustomization.yaml
  - k8s/base/kustomization.yaml
  - k8s/overlays/local/kustomization.yaml
  - k8s/overlays/local/configmap-patch.yaml
  - k8s/overlays/local/secrets-patch.yaml
  - k8s/overlays/local/deployment-api-patch.yaml
  - k8s/overlays/local/deployment-worker-patch.yaml
  - k8s/overlays/local/service-patch.yaml
  - k8s/overlays/local/monitoring/kustomization.yaml
  - k8s/overlays/local/monitoring/prometheus-configmap.yaml
  - k8s/overlays/local/monitoring/alerting-rules-configmap.yaml
  - k8s/overlays/local/monitoring/prometheus-deployment.yaml
  - k8s/overlays/local/monitoring/prometheus-service.yaml
  - k8s/overlays/local/monitoring/grafana-deployment.yaml
  - k8s/overlays/local/monitoring/grafana-service.yaml
  - scripts/deploy-local.ps1
  - scripts/teardown-local.ps1
tests:
  - kustomize build validation (kubectl kustomize --load-restrictor LoadRestrictionsNone)
---

## Prompt

Implement the following plan:

# Local Kubernetes Deployment Plan

The CRM Digital FTE Factory app needs local Kubernetes deployment using the Docker Hub image `syedagulzarbano/agent-maturity-model`. Existing k8s/ manifests target production (3 replicas, TLS ingress, HPA) and have several bugs (wrong image name, missing POSTGRES_PASSWORD, command path mismatches). Use Kustomize overlays to keep production manifests untouched and layer local-dev overrides on top.

## Response snapshot

Implemented full local Kubernetes deployment using Kustomize overlays with 17 new files:

**Base kustomization** (`k8s/kustomization.yaml`): Root production kustomization including all manifests (HPA, ingress). Separate `k8s/base/kustomization.yaml` excludes HPA and ingress for the local overlay.

**Local overlay** (`k8s/overlays/local/`): 6 patch files that fix 9 identified issues:
- Image rewrite: `fte-digital-agent:latest` → `syedagulzarbano/agent-maturity-model:latest`
- Replicas: 3 → 1 for both API and worker
- API command: `api.main:app` → `production.api.main:app`
- Worker command: `python -m workers` → `python -m production.workers`
- Service: ClusterIP → NodePort:30080
- Secrets: Added POSTGRES_PASSWORD (base64 `fte_password`)
- Config: DEBUG logging, permissive CORS
- Namespace: fte-production → fte-local via JSON patch
- Excluded HPA and ingress from base reference

**Monitoring** (`k8s/overlays/local/monitoring/`): Prometheus (v2.48.0, NodePort:30090) and Grafana (10.2.0, NodePort:30030) with SLO alerting rules as ConfigMaps.

**Scripts**: `deploy-local.ps1` automates minikube start, kustomize apply, schema migration, health checks, and URL output. `teardown-local.ps1` tears down resources with optional minikube stop/delete.

Kustomize build validated successfully producing correct output for all 6 pods in fte-local namespace.

## Outcome

- ✅ Impact: Complete local K8s deployment pipeline with monitoring, fixing 9 production manifest issues
- 🧪 Tests: kustomize build produces valid YAML with all transformations applied correctly
- 📁 Files: 17 new files created (14 K8s manifests + 2 scripts + 1 root kustomization update)
- 🔁 Next prompts: Run deploy-local.ps1 to verify end-to-end deployment on minikube
- 🧠 Reflection: Kustomize load restrictor was needed due to overlay referencing parent directory resources; standard pattern for monorepo K8s setups

## Evaluation notes (flywheel)

- Failure modes observed: Kustomize cycle detection when overlay lives inside base directory; namespace mismatch in patches (patches must match pre-transformation namespace)
- Graders run and results (PASS/FAIL): kustomize build validation PASS
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): Add Helm chart alternative for teams preferring Helm over Kustomize
