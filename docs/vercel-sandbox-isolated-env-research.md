# Vercel Sandbox Isolated Environment Research

## Executive Summary
- Vercel Sandbox (beta) provisions Firecracker microVMs programmatically via the `@vercel/sandbox` SDK, built for running untrusted or AI-generated code with configurable runtime, CPU, memory, and ports up to four exposed per sandbox. https://vercel.com/docs/vercel-sandbox https://vercel.com/changelog/run-untrusted-code-with-vercel-sandbox https://vercel.com/changelog/vercel-sandbox-increases-concurrency-and-port-limits
- Sandboxes authenticate using Vercel OIDC tokens or access tokens and can be created from Git repos or inline files, making it feasible for the platform backend to spin up per-user project environments sourced from Azure Container Registry images or Git snapshots. https://vercel.com/docs/vercel-sandbox https://vercel.com/docs/vercel-sandbox/examples
- Pricing is usage-based (Active CPU, provisioned memory, bandwidth, creations) with concurrency limits (10 Hobby, 2000 Pro/Enterprise) and 45-minute max runtime, so orchestration must recycle sandboxes and budget for cost spikes. https://vercel.com/docs/vercel-sandbox/pricing
- Vercel’s SDK surfaces sandbox domains (`sandbox.domain(port)`) and log streams, enabling the MVP web app to activate environments on demand, proxy `/messages` calls to Goose APIs, and tear them down after inactivity similar to the Kubernetes plan but without managing clusters. https://vercel.com/docs/vercel-sandbox https://vercel.com/docs/vercel-sandbox/examples

## Research Iterations
### Iteration 1 – Understand Vercel Sandbox Capabilities
- Vercel Sandbox provides ephemeral compute optimized for AI agent workloads, running inside isolated microVMs with Node.js 22 or Python 3.13 images, `sudo` access, and Amazon Linux 2023 base packages. https://vercel.com/docs/vercel-sandbox https://vercel.com/docs/vercel-sandbox/reference/readme
- Sandboxes can run for up to 45 minutes (default 5) with configurable `timeout`, `ports`, `resources.vcpus`, and support up to 4 open ports. https://vercel.com/docs/vercel-sandbox https://vercel.com/docs/vercel-sandbox/pricing

### Iteration 2 – Authentication & Lifecycle
- The SDK prefers Vercel OIDC tokens (`VERCEL_OIDC_TOKEN`) but allows static access tokens plus `teamId`/`projectId` for server-side automation. https://vercel.com/docs/vercel-sandbox
- Sandbox creation returns handles to write files, run commands, stream logs, and shut down (`sandbox.close()`). https://vercel.com/docs/vercel-sandbox/reference/readme
- Vercel Observability (Dashboard → Project → Observability → Sandboxes) tracks command history, status, and resource usage for audit trails. https://vercel.com/docs/vercel-sandbox

### Iteration 3 – Resource Limits & Scaling
- Each sandbox supports up to 8 vCPUs with 2 GB RAM per vCPU; concurrency limits raised to 2,000 for Pro/Enterprise as of August 18, 2025. https://vercel.com/docs/vercel-sandbox/pricing https://vercel.com/changelog/vercel-sandbox-increases-concurrency-and-port-limits
- Usage billed by Active CPU, provisioned memory GB-hours, network egress/ingress, and sandbox creations; Hobby includes 5 CPU hours, 420 GB-hr, 20 GB network, 5,000 creations. https://vercel.com/docs/vercel-sandbox/pricing

### Iteration 4 – Example Flows & AI Use Cases
- Guides show how to run AI-generated code by writing files then executing commands; logs and stdout stream back to the caller for display. https://vercel.com/guides/running-ai-generated-code-sandbox
- Examples demonstrate cloning private Git repos, running dev servers, exposing ports, and retrieving sandbox domains for browser access. https://vercel.com/docs/vercel-sandbox/examples https://vercel.com/changelog/run-untrusted-code-with-vercel-sandbox

### Iteration 5 – Ecosystem & Roadmap Signals
- Vercel Ship 2025 recap highlights Sandbox as part of Fluid compute and Active CPU pricing strategy, indicating continued investment. https://vercel.com/blog/vercel-ship-2025-recap
- Third-party recaps reinforce use cases for executing AI agent workloads securely. https://dev.to/devy/recap-of-vercel-ship-2025-52m3

## Proposed Architecture Adaptation
1. **User → Sandbox Mapping**: Instead of namespaces, create one sandbox per project activation request. Persist project metadata in MongoDB, including sandbox IDs, status, ports, and assigned domain.
2. **Image Distribution**: Host Goose API container image in Azure Container Registry; upon activation, copy image artifacts into sandbox via OCI pull (using `docker` or `ctr` inside sandbox) or clone from Git repo that includes Docker build context.
3. **Startup Workflow**:
   - Backend calls `Sandbox.create({ runtime: 'node22', ports: [3001], timeout: ms('30m'), resources: { vcpus: 2 } })`.
   - Upload project code or fetch from Git, install dependencies, and start Goose API server on port 3001.
   - Call `sandbox.domain(3001)` to retrieve public URL; store in MongoDB and return to frontend.
   - Optionally tunnel traffic through backend proxy for additional authentication.
4. **Access Control**: Backend controls sandbox creation and maintains mapping of `userId → sandboxId`. Frontend requests go through backend, which validates user/project ownership before forwarding to sandbox domain or streaming responses.
5. **Deactivation**: On user exit or timeout, invoke `sandbox.close()`; optionally snapshot conversation state to MongoDB and delete sandbox record.
6. **Monitoring**: Use Vercel Observability for runtime telemetry and integrate API responses to display logs in the admin UI.
7. **Cost Controls**: Track Active CPU/GB-hr per project; implement inactivity timers to close sandboxes automatically before hitting 45-minute limit or concurrency caps.

## Command & Code Snippets
```ts
import { Sandbox } from '@vercel/sandbox';
import ms from 'ms';

const sandbox = await Sandbox.create({
  runtime: 'node22',
  ports: [3001],
  resources: { vcpus: 2 },
  timeout: ms('30m'),
});

await sandbox.runCommand({
  cmd: 'dnf',
  args: ['install', '-y', 'docker'],
  sudo: true,
});

await sandbox.runCommand({
  cmd: 'docker',
  args: ['run', '--rm', '-p', '3001:3001', 'caf0957b5c26acr.azurecr.io/goose-api-server:2409251544'],
});

const apiUrl = sandbox.domain(3001);
console.log('Sandbox endpoint:', apiUrl);

// Later, when project closes
await sandbox.close();
```
- Domains returned by `sandbox.domain(port)` resolve publicly while the sandbox runs. https://vercel.com/docs/vercel-sandbox/examples
- `sandbox.runCommand` streams logs/stdout enabling UI to show activation progress. https://vercel.com/docs/vercel-sandbox/reference/readme

## Operational Considerations
- **Timeout Handling**: Implement heartbeat pings; if user inactive for N minutes, call `sandbox.close()` to avoid idle billing.
- **State Persistence**: Goose API session data should persist to MongoDB (existing sessions collection) since sandbox filesystem resets after shutdown.
- **Security**: Restrict backend API to internal users; never expose Vercel tokens to frontend. Consider running backend on Vercel with OIDC auto-rotation.
- **Region Constraint**: Sandboxes currently run in `iad1`; confirm latency acceptable for U.S.-based users and plan for multi-region when released.

## Open Implementation Questions
1. How will we package the Goose API runtime for sandboxes—prebuilt OCI image pulled via container runtime, or node project installed via `pnpm` inside sandbox?
2. What is the best mechanism for authenticating frontend requests to sandbox domains—backend proxy, signed URLs, or per-request token injection?
3. Can we cache dependencies between sandbox runs (e.g., using `sandbox.attachVolume`) or must each activation reinstall from scratch, affecting performance and cost?
4. How do we manage concurrency bursts if multiple projects activate simultaneously; do we need a queue or pooling layer to stay within concurrency quotas (10 Hobby vs 2000 Pro)?
5. Are there compliance or data residency requirements that conflict with the single `iad1` region availability during beta?
6. What observability hooks do we need to surface sandbox logs/errors in the MVP UI (websocket streaming vs polling Vercel Observability APIs)?
7. Should we design a scheduler to reuse long-lived sandboxes across requests for the same project to avoid cold starts, or is full teardown per exit acceptable?

