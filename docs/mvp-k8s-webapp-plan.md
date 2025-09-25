# MVP Web App Plan – Kubernetes-Isolated User Environments

## Goal
Deliver a proof-of-concept web application that lets an operator pick a user, manage that user’s projects, and activate/deactivate isolated Kubernetes environments per project. Each environment runs a container image pulled from Azure Container Registry (ACR) and exposes the Goose API server for `/messages` interactions.

## Key Assumptions
- Authentication/authorization out of scope; “user selection” is a drop-down populated from a static list or seed data.
- A managed Kubernetes cluster (e.g., AKS) already exists, and the backend has `kubectl` + kubeconfig access with sufficient RBAC to create namespaces, deployments, services, and scale workloads.
- ACR holds the Goose API image; image URL and tag are the same for all projects in the MVP.
- Each user maps 1:1 to a Kubernetes namespace named `user-<id>`.
- MongoDB is available (reuse Goose sessions database); the projects collection will persist project metadata, replacing the earlier in-memory-store assumption.

## High-Level Architecture
- **Frontend (SPA or server-rendered minimal UI)**
  - Dropdown for user selection; shows user’s projects with status badges (Active/Inactive).
  - CRUD controls: Create Project, Rename, Delete.
  - Buttons to Activate / Deactivate, and a link or embedded console for `/messages` interaction.
  - Web UI can be simple React/Vue or server-side templating (e.g., FastAPI + Jinja) given MVP scope.
- **Backend API**
  - Responsible for project CRUD, activation/deactivation, and proxying `/messages` requests to the project’s Goose API endpoint.
  - Persists project metadata in MongoDB collection `projects` (schema: `_id`, `user_id`, `project_id`, `name`, `namespace`, `deployment`, `service`, `ingress`, `status`, `endpoint`, timestamps). Reads from MongoDB on startup to rebuild runtime cache.
  - Uses a Kubernetes client (Python `kubernetes` client, Go client-go, or shelling out to `kubectl`) to:
    - Ensure namespace exists for the user on first use.
    - Create/update/delete Deployment, Service, Ingress resources per project.
    - Scale Deployment replicas between 0 and 1.
    - Query Ingress/Service for FQDN/IP after activation.
  - Provides `/messages` endpoint proxy: `POST /users/:userId/projects/:projectId/messages` -> fetch project endpoint from store -> `POST` to Goose API `/messages` in the user pod; stream responses back to caller.
- **Kubernetes Assets per Project**
  - `Namespace`: created once per user with labels/annotations for Pod Security and quotas (reuse manifests from research doc).
  - `Deployment`: name `proj-<id>-api`, image from ACR, env vars include `USER_ID`, `PROJECT_ID`. Start with `replicas: 0`.
  - `Service`: ClusterIP exposing container port 3001 (matching Goose API).
  - `Ingress` or `HTTPRoute`: host `proj-<id>.user-<id>.<base-domain>`, TLS optional in MVP (can use plain HTTP on internal network).
  - Optional `NetworkPolicy` to allow inbound only from backend namespace.

## Implementation Steps
1. **Bootstrap Project Skeleton**
   - Choose language/runtime (e.g., Python FastAPI for rapid backend + simple frontend templates).
   - Scaffold API routes:
     - `GET /users` (static list)
     - `GET /users/:id/projects`
     - `POST /users/:id/projects`
     - `PUT /users/:id/projects/:projectId`
     - `DELETE /users/:id/projects/:projectId`
     - `POST /users/:id/projects/:projectId/activate`
     - `POST /users/:id/projects/:projectId/deactivate`
     - `POST /users/:id/projects/:projectId/messages`
2. **MongoDB Integration**
   - Reuse connection code patterns from Goose sessions (`database.rs` reference) to configure client (connection string + database name env vars).
   - Define `projects` collection schema (e.g., in Python Pydantic/ODM or Go structs) with indices on `user_id` and `project_id`.
   - Implement repository module with CRUD: `list_projects(user_id)`, `create_project`, `update_project`, `delete_project`, `get_project(project_id)`.
   - Optionally maintain an in-memory cache synchronized with MongoDB for quick access, but treat MongoDB as source of truth.
3. **Kubernetes Integration Layer**
   - Wrap kubectl commands or use Kubernetes client library (preferred for reliability).
   - Functions:
     - `ensure_namespace(userId)` -> create namespace, apply PodSecurity label, ResourceQuota (optional for MVP).
     - `apply_project_resources(userId, project)` -> create/update Deployment, Service, Ingress manifests using templates with placeholders; persist resulting resource names in MongoDB.
     - `scale_project(userId, projectId, replicas)` -> patch Deployment.
     - `get_project_endpoint(userId, projectId)` -> wait for Service/Ingress ready; return FQDN/IP.
     - `delete_project_resources(userId, projectId)` -> delete K8s objects.
   - Decide on templating (e.g., Jinja templates rendered to YAML then `kubectl apply -f -`).
   - On backend startup, reconcile cluster state with Mongo: list namespaces/deployments for known users, update status fields, and flag drift (e.g., missing deployments) for operator review.
4. **Activation Flow**
   - On `activate`:
     1. Ensure namespace exists.
     2. Apply Deployment/Service/Ingress manifests if not present.
     3. Scale Deployment to 1.
     4. Poll `kubectl get pods` until Ready.
     5. Fetch Ingress hostname or fallback to port-forward as temporary solution.
     6. Persist `status=active`, endpoint, and last-activated timestamp in MongoDB (and cache if used).
   - On `deactivate`: scale Deployment to 0, optionally confirm pods terminated, update MongoDB status to `inactive`.
5. **Messages Proxy**
   - For active project, `POST` to `http://<endpoint>/api/v1/sessions/...` as described in API docs.
   - MVP simplification: auto-create a session per request or reuse cached session ID per project.
   - Stream SSE back to caller or buffer entire response (MVP can capture entire response before returning).
6. **Frontend Wiring**
   - Minimal UI: simple forms calling backend endpoints via fetch/Axios.
   - Display environment status, activation button, `messages` form posting to backend and showing response text.
7. **Configuration**
   - Environment variables for: `KUBECONFIG` path, `ACR_IMAGE` (e.g., `myregistry.azurecr.io/goose-api:latest`), base domain for ingress, optional `NAMESPACE_PREFIX`, `MONGO_URI`, `MONGO_DB` and `PROJECTS_COLLECTION`.
   - For local dev, use port-forward to talk to cluster or run app inside cluster.
8. **Observability & Logging**
   - Log kubectl command output and errors.
   - Surface activation failures to UI.
   - Log MongoDB CRUD operations with correlation IDs for traceability.
9. **Cleanup Procedures**
   - On project delete: scale to 0, delete Deployment/Service/Ingress, remove record from MongoDB (and cache if used).
   - Optional: delete namespace when user has zero projects (for long-term cluster hygiene).

## Open Questions / Risks
- How do we secure backend access to the cluster when running outside the operator’s network? (store kubeconfig securely, consider Azure workload identity).
   - Answer: no security necessary for now. This is just a PoC
- Should the MVP implement SSE streaming for `/messages`, or is collecting full response acceptable?
   - SSE is required
- What base domain/ingress controller will be available in the cluster? (NGINX, AGIC, or internal service?).
   - this can be decided. Take the basic one
- How to handle cleanup if backend crashes—do we need reconciliation on startup (list namespaces/projects and sync state)?
   - assume it wont crash. No resilliance for now. This is a poc.
- Do we require migrations/seed scripts for the `projects` collection (default indexes, sample data) tied to deployment pipeline?
   - no, nothing

