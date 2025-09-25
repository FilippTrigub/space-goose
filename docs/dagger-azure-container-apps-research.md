# Dagger Container-Use + Azure Container Apps Research

## Executive Summary
- Dagger's `container-use` API lets the agent run commands inside a dedicated OCI container that persists across steps via mounts and caches, providing an isolated coding sandbox per user workflow.citeturn1search0
- Azure Container Apps supplies private environments with VNet integration, secrets, managed identity, and ingress restrictions to keep each sandboxed replica accessible only to authorized callers.citeturn2search0turn5search0
- A Dagger pipeline can build and push images to Azure Container Registry using community Azure modules, then execute Azure CLI (`az containerapp`/jobs) commands to provision or update per-user container apps.citeturn1search0turn4search0turn3search0
- Key risks involve secret distribution, identity mapping, and timely teardown so Dagger and Azure quotas are not exhausted by lingering sandboxes.citeturn1search0turn2search0

## Context & Goals
Enable an AI coding agent to spin up an isolated execution environment for each user. Dagger orchestrates build and deployment, while Azure Container Apps hosts the long-lived or on-demand container per user app ID.

## Research Iterations
### Iteration 1 – Understand Dagger Container-Use Capabilities
- `container-use` keeps the same container running through a pipeline, supports copying sources into the container, executing commands, and exporting artifacts—ideal for preparing a user’s workspace before deployment.citeturn1search0
- Dagger SDKs (Go, Python, TypeScript) expose composable pipelines; the Daggerverse Azure module offers helpers to authenticate with Azure and interact with registries.citeturn1search0

### Iteration 2 – Map Azure Container Apps Isolation Features
- Container Apps environments isolate workloads with per-environment policies, VNet routing, secrets, and managed identities, supporting per-tenant security controls.citeturn2search0
- Ingress can be limited to internal traffic or allowed only from specific sources using rate limits and network policies, ensuring replicas are reachable solely by their owner app.citeturn5search0

### Iteration 3 – Integrate Dagger Pipelines with Azure Deployment
- Use Dagger to tag and push container images into Azure Container Registry via the Azure module or direct `docker`/`az acr` commands scripted in the pipeline.citeturn1search0turn4search0
- Provision a corresponding Container App or trigger a Container Apps Job with Azure CLI; jobs support scheduled or on-demand execution for ephemeral agent runs.citeturn4search0turn3search0

## Key Findings
- **Isolated Build + Runtime Flow**: Build the user-specific workspace inside Dagger’s persistent container, produce an image, push it to ACR, and hand off deployment to Azure Container Apps.citeturn1search0turn4search0
- **Provisioning Pattern**: Script `az containerapp create` or job execution inside the Dagger pipeline to spin up or refresh per-user replicas (set `--min-replicas` for persistent sandboxes; use jobs for ephemeral tasks).citeturn4search0turn3search0
- **Security Controls**: Apply Container Apps environment policies (private ingress, VNet, managed identity, secrets) so each replica only accepts traffic from its owning application tier.citeturn2search0turn5search0
- **Lifecycle Management**: Track user-to-replica metadata (labels, tags) and issue `az containerapp delete` or stop job executions when sessions end to reclaim compute and stay within quotas.citeturn4search0turn2search0
- **Scalability Considerations**: Container Apps environments share infrastructure; monitoring per-environment resource limits and using rate limiting/ingress controls prevents noisy neighbors and protects Azure quotas.citeturn2search0turn5search0

## Follow-Up Questions
1. How will Azure credentials (service principal, workload identity) be injected into the Dagger pipeline without exposing them to user code inside the sandbox?citeturn1search0
2. Should persistent sandboxes run as always-on container apps with internal ingress, or should we trigger Container Apps Jobs and persist state in external storage?citeturn3search0turn2search0
3. What network and ingress policies (private endpoints, specific source IPs, rate limits) best enforce per-user isolation at the Container Apps environment layer?citeturn5search0turn2search0
4. Which observability tools (Log Analytics workspace, Azure Monitor alerts) will surface deployment or runtime failures back to the AI agent orchestrator?citeturn2search0
5. Can we pre-warm Dagger container-use caches or base images to reduce build times while still ensuring each user’s code runs in a clean environment?citeturn1search0

