n8n API Node Implementation Plan

Context
- Goal: build an n8n programmatic action node that accepts incoming items, orchestrates one or more Goose API calls, and emits structured results.
- The Goose control plane is already deployed (Space Goose CLI). All calls use the shared base URL and must include an `X-API-Key` header provided by the user (display label `BLACKBOX_API_KEY`).
- Each workflow run targets a specific `project_id`; the node must ensure the project is active (backend enforces a 120-second activation timeout), route traffic to a session, and optionally stream assistant output.

Research Highlights
- n8n recommends capturing integration requirements first, then choosing node type and UX before coding; programmatic nodes unlock custom `execute()` logic suitable for sequenced HTTP calls.
- Node description metadata drives the UI; separate description files keep properties tidy while `execute()` focuses on behavior.
- Credentials classes can inject headers automatically so runtime logic stays focused on orchestration.
- Transport helpers (e.g., `generic.request.ts`) make it easy to reuse authentication, retry, and streaming code across multiple request hops.

Implementation Roadmap
1. Requirements & API Mapping
   - Document all Goose endpoints required for the workflow: `GET /projects`, `POST /projects/{project_id}/activate`, `GET /projects/{project_id}/sessions`, `POST /projects/{project_id}/sessions`, `POST /projects/{project_id}/messages`, `POST /projects/{project_id}/messages/send`, and `GET /projects/{project_id}/agent/status` for readiness checks.
   - Capture request/response schemas (status field states, session structures, SSE payload shapes) plus failure codes returned by FastAPI wrappers.
   - Note per-call headers: every request needs `X-API-Key`; POST bodies rely on JSON with `Content-Type: application/json`.
2. Decide Node Type & Style
   - Use an action node that consumes input items and returns outputs; no trigger behavior is required because workflows start elsewhere.
   - Choose the programmatic style template so `execute()` can branch between activation, session management, streaming vs fire-and-forget send, and optional multi-call sequences.
3. Project Scaffolding
   - Run `npx n8n-node-dev new` and select programmatic node + credentials scaffolds.
   - Configure package metadata (`name`, `keywords`, `n8n` tags) and install any dependencies needed for SSE parsing (e.g., `eventsource-parser` if the built-in helpers are insufficient).
4. File Structure & Boilerplate
   - Keep `nodes/SpaceGoose/SpaceGoose.node.ts` as the entry, with `SpaceGoose.node.description.ts` housing `description.properties` definitions.
   - Add `nodes/SpaceGoose/transport/goose.client.ts` (or similar) that wraps HTTP calls, merges headers, handles retries/backoff, and exposes helpers for streaming reads.
   - Place shared TypeScript interfaces (project/session/message payloads) under `nodes/SpaceGoose/interfaces.ts` to avoid magic strings in `execute()`.
5. UI & UX Definition
   - Required fields: `projectId` (string), message/payload inputs, and boolean `captureOutput` to select streaming vs synchronous send.
   - Optional fields: `sessionId` (reuse existing) and `sessionName` (label used when auto-creating). Use collections + `displayOptions` so `sessionName` appears only when `sessionId` is empty and auto-create is enabled.
   - Include helper text explaining activation happens automatically (up to 120 seconds) and that `X-API-Key` is sourced from credentials.
6. Credentials & Header Management
   - Implement `credentials/SpaceGooseApi.credentials.ts` with a single field labeled `BLACKBOX_API_KEY` (secure, masked, optional env var).
   - In `authenticate`, inject `X-API-Key` into every request; allow additional static headers if future endpoints require them.
   - Support custom base URLs as an advanced option if deployments diverge later, defaulting to the shared production URL.
7. Execution Logic
   - For each incoming item:
     a. Resolve credentials (base URL + API key).
     b. Retrieve project metadata via `GET /projects` and locate the chosen `project_id`; throw a helpful error if not found.
     c. If project `status` is not `active`, `POST /projects/{project_id}/activate` then poll `/projects/{project_id}/agent/status` until `project_status` indicates readiness or a backend timeout occurs (120 seconds handled server-side; surface timeout/error details to the user).
     d. Session handling:
        - If `sessionId` input is provided, validate it exists via `GET /projects/{project_id}/sessions`; error if missing unless `continueOnFail` is set.
        - If `sessionId` is omitted, auto-create one with `POST /projects/{project_id}/sessions` (using `sessionName` or a generated label) and capture the returned ID.
     e. Send the payload:
        - When `captureOutput` is true, call `POST /projects/{project_id}/messages` with `{ content, session_id }`, consume the SSE stream, and collect assistant text/tool events for the output item.
        - When false, call `POST /projects/{project_id}/messages/send` and map the JSON response into the output. Multi-message batching is out of scope and unsupported by the API.
     f. Record diagnostics (session ID, mode, response metadata) in the returned item.
   - Respect `continueOnFail` by emitting error info without halting the whole batch when possible.
8. Testing & Validation
   - Unit-test transport helpers (header merging, SSE parser) and the activation/session orchestration logic using mocked HTTP clients.
   - Add integration-style tests with `n8n-node-dev test` leveraging fixtures that simulate the FastAPI responses.
   - Manual QA: load the node into a local n8n instance, run against a staging Goose API, verify both streaming and fire-and-forget paths, activation edge cases, and session reuse.
9. Documentation & Distribution
   - Extend the package README with setup instructions (create API key, find `project_id`, choose streaming mode) and troubleshooting tips (activation timeouts, invalid sessions).
   - Provide workflow examples: (1) send instructions and capture assistant output, (2) fire-and-forget command chain.
   - When stable, publish the node or bundle it with internal automations.

Project & Session Workflow Requirements
- Project lookup: `GET /projects` returns an array; filter by `id` to obtain `status`, `sessions`, and repo metadata.
- Activation: `POST /projects/{project_id}/activate` kicks off backend-managed scaling with a 120-second timeout. Poll `/projects/{project_id}/agent/status` until ready; surface backend timeout errors but do not expose extra controls in the node UI.
- Session lifecycle: `sessionId` input is optional. When provided, validate via `GET /projects/{project_id}/sessions`; when omitted, auto-create with `POST /projects/{project_id}/sessions` and store the new ID.
- Messaging endpoints:
  * Streaming capture → `POST /projects/{project_id}/messages` with `{ session_id, content }`, read SSE events (`message`, `tool_request`, `tool_response`, `thinking`, etc.) and assemble rich output.
  * Fire-and-forget → `POST /projects/{project_id}/messages/send` with the same body; wait for JSON reply containing final result only.
- Error scenarios to cover: inactive project (400), missing session (404), Goose API connectivity (500), SSE JSON decoding issues, activation timeout.

Node Output Model
- Required: `projectId`, `sessionId` (provided or newly created), `mode` (`stream` | `send`), `responseText` (aggregated assistant text or result).
- Optional: `rawEvents` (array for downstream tooling), `createdSession` (boolean), and any `toolEvents` extracted from SSE payloads.

Open Questions / Follow-Ups
- None at this time; requirements above are approved.

Next Steps
- Confirm naming and grouping for UI properties (e.g., collections vs plain fields) before scaffolding.
- Kick off node scaffolding with `npx n8n-node-dev new` once API schemas are captured in TypeScript interfaces.
