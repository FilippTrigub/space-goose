# Azure Container Apps Isolated Environment Research

## Executive Summary
- Azure Container Apps dynamic sessions offer per-identifier sandboxes with Hyper-V isolation and REST-managed lifecycles, but they auto-expire after a configurable cooldown and remain in public preview with regional limits.citeturn5search0turn5search4turn10view0
- A durable alternative is to provision one container app (or revision) per tenant and pin min/max replicas, using internal ingress, IP restrictions, and VNet integration to scope traffic to the owning user app.citeturn6search3turn5search6turn0search1turn7search3turn0search2
- Built-in Microsoft Entra authentication, managed identities, and session-level RBAC enforce user binding without embedding secrets, keeping replica APIs reachable only to authorized callers.citeturn1search0turn1search1turn10view0turn8search3
- Quotas (for replicas and session pools), pricing mechanics, and preview constraints shape capacity planning and should inform automation, monitoring, and fallback design.citeturn5search5turn5search6turn5search2

## Requirements Recap
- Each user application must receive an isolated compute environment ("replica") that persists with the user app lifecycle.
- The replica must expose an API accessible only to that user app ID.
- Provisioning should be automated when a user creates an environment; deprovision when the app is removed.

## Isolation Patterns in Azure Container Apps
### Dynamic Sessions (Preview)
- Sessions run in Hyper-V sandboxes managed by a session pool; requests use an app-defined identifier (e.g., user ID) that allocates or reuses a session.citeturn5search0turn10view0
- Cooldown destroys inactive sessions; you can set the cooldown (e.g., 600 seconds) but long-lived sessions are not guaranteed indefinitely, so additional state persistence is needed for user apps that must outlive inactivity.citeturn10view0
- Sessions accept traffic via a dedicated management endpoint secured by Microsoft Entra tokens and the `Azure ContainerApps Session Executor` role, enabling per-user scoping at the API gateway or backend.citeturn10view0
- Preview status limits regions and workloads (code interpreter vs. custom container) and should be validated for production SLAs.citeturn5search4turn5search2

### Dedicated Container App Per Tenant
- Automate `az containerapp create` (or Bicep/ARM REST) to spin up a container app per user with controlled min/max replicas (`--min-replicas 1`, `--max-replicas 1`) so the app persists and remains single-tenant.citeturn6search3turn6search1turn5search6
- Use internal ingress and private DNS so only upstream services within the environment can reach the replica; expose public endpoints via a shared gateway if needed.citeturn0search1turn0search2
- IP ingress restrictions provide an allow-list of source CIDRs (e.g., API gateway subnet or NAT IP) to bind traffic to the owning user app.citeturn7search3
- Revision labels can map stable URLs per tenant while keeping latest revision traffic routing separate from per-tenant endpoints.citeturn9search1

### Shared App with Sticky Sessions (Supplemental)
- Session affinity keeps a given client on the same replica using cookies, but it does not guarantee exclusivity; it augments but cannot replace hard tenancy controls.citeturn5search1turn5search3

## Access Control and Networking
- Configure ingress as internal by default, or external with IP restrictions and client-certificate enforcement to limit callers to known frontends.citeturn0search1turn7search1turn7search3
- Integrate Microsoft Entra authentication (Easy Auth) to require tokens before replica APIs run; combine with managed identities for service-to-service authentication tied to user app principals.citeturn1search0turn1search1turn8search3
- VNet integration enables NSGs, private endpoints, and route control so replicas can live in subnets reachable only from the platform orchestrator.citeturn0search2turn0search3
- Dynamic sessions default to egress-disabled networking; explicitly configure session network mode if user workloads need outbound calls, and audit risks when enabling managed identity in sessions.citeturn10view0

## Lifecycle Automation
- `containerapp up` and Bicep templates (`Microsoft.App/containerApps@2025-01-01`) provision environments, supporting infrastructure-as-code for per-user deployments.citeturn6search3turn6search1
- Automate revision and label management (e.g., map label = user ID) via `az containerapp revision` commands to orchestrate rolling updates without downtime.citeturn9search1
- Session pools expose REST APIs for create/delete operations; integrate pool management into onboarding flows to allocate user-specific sessions or containers.citeturn10view0

## Operational CLI Reference
- **Create with env vars**: deploy from an Azure Container Registry image while injecting configuration using `--env-vars` (space-separated `KEY=VALUE` pairs).
  ```sh
  az containerapp create \
    --name <APP_NAME> \
    --resource-group <RESOURCE_GROUP> \
    --environment <CONTAINER_APPS_ENV> \
    --image <REGISTRY_SERVER>/<IMAGE>:<TAG> \
    --env-vars GREETING="Hello" FEATURE_FLAG=true
  ```
  citeturn3view1
- **Fetch FQDN**: query the ingress hostname that Azure assigns to the container app for wiring traffic or storing per-tenant metadata.
  ```sh
  az containerapp show \
    --resource-group <RESOURCE_GROUP> \
    --name <APP_NAME> \
    --query properties.configuration.ingress.fqdn -o tsv
  ```
  citeturn8view1
- **Start/stop replicas**: suspend or resume compute as needed during user offboarding or maintenance windows.
  ```sh
  az containerapp stop --name <APP_NAME> --resource-group <RESOURCE_GROUP>
  az containerapp start --name <APP_NAME> --resource-group <RESOURCE_GROUP>
  ```
  citeturn9view1

## Scaling, Quotas, and Cost
- Default replica quotas allow up to 300 replicas via portal (1,000 via CLI) per revision; session pools default to six per subscription with 10,000 sessions, influencing capacity design.citeturn5search5
- Consumption pricing bills active replicas per vCPU and GiB-second, with idle rates when min replicas are configured; factor this into per-user cost models.citeturn5search6
- Preview features (dynamic sessions) may have separate pricing and SLA considerations; monitor Azure roadmap for GA timelines.citeturn5search2turn5search4

## Gaps and Risks
- Dynamic sessions remain preview-only; production workloads may need mitigations (e.g., fallback to dedicated app instances) until GA.citeturn5search2
- Region availability for sessions is limited; ensure user tenancy aligns with supported geographies or plan cross-region strategies.citeturn5search2
- Per-tenant container apps increase environment count; monitor quotas and automation limits to avoid throttling.citeturn5search5
- Managed identity use inside sessions can expose elevated credentials to user code; enforce least privilege and consider keeping identity disabled in session runtime.citeturn10view0

## Implementation Questions & Next Research Targets
1. Which tenancy model aligns with the product roadmap—dynamic sessions, per-tenant apps, or a hybrid—and what SLAs are required?
2. How will the platform authenticate user apps to their replicas (JWT claims, mutual TLS, private networking), and which Azure identity objects represent the user app?
3. What onboarding/offboarding automation is needed (IaC templates, Azure Functions, or Logic Apps) to create/update/delete container apps or session identifiers when user apps change state?
4. How will state persistence (databases, storage) be isolated per user to complement compute isolation?
5. What monitoring and alerting (Log Analytics tables, Azure Monitor alerts) should track replica health, unauthorized access attempts, or quota exhaustion?
6. Are there compliance constraints (data residency, preview features) that preclude using dynamic sessions in certain regions or customer segments?
7. How will cost controls be enforced (budgets, auto-deprovision rules) to prevent runaway replica usage per tenant?
8. If latency matters, what networking topology (internal ingress vs. gateway) ensures minimal hops between the user app and its isolated replica?
