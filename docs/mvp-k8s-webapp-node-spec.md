# Node.js MVP Specification – Kubernetes-Isolated User Environments

## Goal
Deliver a proof-of-concept web experience where an operator selects a user, manages that user’s projects, and activates/deactivates isolated Kubernetes environments per project. Activation pulls a Goose API container image from Azure Container Registry (ACR) and exposes the `/messages` endpoint to the web UI. Implementation targets a Node.js codebase deployable on Vercel for the UI and (if feasible) for backend APIs.

## High-Level Architecture
- **Next.js 15 App Router**
  - Server components for dashboard views; client components for interactive project CRUD and messaging UI.
  - Route Handlers (`app/api/*`) implement REST endpoints consumed by the frontend and any automation clients.
- **Backend Modules (Node)**
  - `kubeClient` built on `@kubernetes/client-node` to handle namespace creation, deployment lifecycle, scaling, and ingress/service queries.
  - `mongoClient` using official `mongodb` driver with connection pooling; configured during Next.js `app` bootstrap via singleton pattern.
  - `projectService` orchestrates CRUD with MongoDB and triggers Kubernetes operations; exposes reconciliation helpers for startup sync.
  - `messagingProxy` streams Goose `/messages` responses to the browser using Node readable streams + Next.js streaming responses.
- **Data Stores**
  - MongoDB database `goose` (reuse existing cluster) with collection `projects`.
  - Optional Redis (future) for transient activation locks; not required for MVP.

## Runtime Environment
- Node.js 20 LTS runtime (default for Vercel Node Functions / Next.js 15).
- Environment variables (managed via Vercel secrets locally through `.env.local`):
  - `MONGODB_URI`, `MONGODB_DB`
  - `ACR_IMAGE` (e.g., `caf0957b5c26acr.azurecr.io/goose-api-server:latest`)
  - `KUBE_CONFIG_BASE64` (base64-encoded kubeconfig) **or** discrete vars (`KUBE_HOST`, `KUBE_TOKEN`, `KUBE_CA`) for client auth
  - `KUBE_NAMESPACE_PREFIX` (default `user-`)
  - `INGRESS_BASE_DOMAIN` (optional; used to compute expected hostnames)
  - `GOOSE_API_PORT` (default `3001`)

## Data Model – `projects` Collection
```json
{
  "_id": ObjectId,
  "user_id": "user-123",
  "project_id": "proj-uuid",
  "name": "Project Name",
  "namespace": "user-123",
  "deployment": "proj-uuid-api",
  "service": "proj-uuid-svc",
  "ingress": "proj-uuid-ingress",
  "status": "inactive" | "activating" | "active" | "deactivating" | "error",
  "endpoint": "https://proj-uuid.user-123.example.com" | null,
  "last_activated_at": ISODate,
  "last_deactivated_at": ISODate,
  "created_at": ISODate,
  "updated_at": ISODate
}
```
Indexes: `{ user_id: 1, project_id: 1 }` (unique), `{ status: 1 }` (optional for filtering).

## API Surface (Route Handlers)
| Method | Path | Description |
| ------ | ---- | ----------- |
| GET | `/api/users` | Returns static list of user IDs + display names. |
| GET | `/api/users/:userId/projects` | List projects for user from MongoDB. |
| POST | `/api/users/:userId/projects` | Create project; inserts Mongo record, provisions namespace (if first project for user), applies manifests, returns project payload. |
| PATCH | `/api/users/:userId/projects/:projectId` | Update name/metadata only. |
| DELETE | `/api/users/:userId/projects/:projectId` | Scale to zero, delete Kubernetes resources, remove Mongo record. |
| POST | `/api/users/:userId/projects/:projectId/activate` | Ensure manifests exist, scale deployment to 1, poll readiness, update Mongo status/endpoint. |
| POST | `/api/users/:userId/projects/:projectId/deactivate` | Scale deployment to 0, record status. |
| POST | `/api/users/:userId/projects/:projectId/messages` | Proxy message body to Goose API `/api/v1/sessions/:sessionId/messages`, stream SSE back to caller. |

## Kubernetes Integration
- Namespace pattern: `user-${userId}`.
- Resource templates assembled via JS objects -> YAML (using `js-yaml`) before applying with Kubernetes client `apply`/`patch` operations.
- Deployment spec enforces security context (runAsNonRoot + numeric UID/GID) and resources (requests/limits) per `docs/kubernetes-isolated-env-research.md`.
- Service type `LoadBalancer` in MVP so each project receives external IP; optionally attach Ingress based on `INGRESS_BASE_DOMAIN`.
- Activation workflow:
  1. call `kubeClient.ensureNamespace(userId)` (creates namespace, labels, quotas, ConfigMap/Secret if needed).
  2. `kubeClient.applyManifests(projectSpec)` (Deployment, Service, optional Ingress/NetworkPolicy).
  3. `kubeClient.scaleDeployment(namespace, name, 1)`.
  4. Poll pod status via `watch` until Ready or timeout (configurable, e.g., 120s).
  5. Fetch Service `status.loadBalancer.ingress` and/or Ingress hostname; persist to Mongo.
  6. Return endpoint to caller.
- Deactivation: scale to 0 and confirm no running pods; update Mongo status.

## Frontend Requirements
- Dashboard page `/`:
  - User selector (predefined list) -> loads projects via SWR/fetch.
  - Project table/cards showing name, status, endpoint link (if active), last activated time.
  - Buttons: Activate, Deactivate, Delete, Edit.
- Project modal / detail view with:
  - Activation logs (pulled from backend streaming endpoint).
  - Simple message console: text area + submit -> posts to `/messages`, streams response (display each SSE chunk in order).
- Minimal styling with TailwindCSS or Chakra UI.

## Messaging Proxy Flow
1. Client POSTs message payload to backend endpoint.
2. Backend ensures project active, obtains endpoint (or triggers activation if flagged as stale).
3. Backend opens SSE stream to Goose API, re-streams data using Web Streams API.
4. Client listens via `EventSource` or streaming fetch to display tokens progressively.

## Error Handling & Logging
- Use `pino` or `winston` for structured logs (JSON). Correlate requests with `x-request-id`.
- Capture Kubernetes API errors (e.g., quota violations) and map to 4xx/5xx responses.
- Update project status to `error` with `error_message` field (optional) for visibility in UI.

## Future Enhancements (beyond MVP)
- Replace LoadBalancer with shared ingress + path routing.
- Introduce background worker (e.g., queue) for long-running activation to avoid hitting Vercel function limits.
- Implement reconciliation on startup to match Mongo records with live cluster state.
- Add auth (e.g., NextAuth) and audit logging.

