# MVP Web App Plan – Vercel Sandbox Isolated User Environments

## Goal
Deliver a proof-of-concept web application that lets an operator pick a user, manage that user's projects, and activate/deactivate isolated Vercel Sandbox environments per project. Each environment runs the Goose API server using Vercel Sandbox microVMs for secure, ephemeral compute isolation.

## Key Assumptions
- Authentication/authorization out of scope; "user selection" is a drop-down populated from a static list or seed data.
- The backend has Vercel API access with `VERCEL_TOKEN`, `VERCEL_TEAM_ID`, and `VERCEL_PROJECT_ID` configured.
- The Goose API will be packaged as a container image in Azure Container Registry OR deployed as a Git repository that can be cloned into sandboxes.
- Each user maps 1:1 to a logical grouping; projects within users are isolated via separate sandbox instances.
- MongoDB is available (reuse Goose sessions database); the projects collection will persist project metadata and sandbox state.
- Sandboxes are ephemeral by design (max 45min for Hobby, 5hr for Pro/Enterprise) and will be recreated as needed.

## High-Level Architecture

### Frontend (Next.js 15 + React 19)
- **User Management**: Dropdown for user selection; shows user's projects with real-time status badges (Creating/Active/Stopping/Inactive/Error).
- **Project CRUD**: Create Project, Rename, Delete with form validation.
- **Environment Controls**: Activate/Deactivate buttons with progress indicators and real-time log streaming.
- **Goose Integration**: Embedded chat interface for `/messages` interaction with active project sandboxes.
- **Real-time Updates**: WebSocket or SSE connection for sandbox status updates, log streaming, and progress feedback.
- **Modern UI**: Built with Next.js 15 App Router, shadcn/ui components, Tailwind CSS for responsive design.

### Backend API (Next.js API Routes)
- **Project Management**:
  - `GET /api/users` - List available users
  - `GET /api/users/[userId]/projects` - List user's projects with status
  - `POST /api/users/[userId]/projects` - Create new project
  - `PUT /api/users/[userId]/projects/[projectId]` - Update project
  - `DELETE /api/users/[userId]/projects/[projectId]` - Delete project and cleanup
- **Sandbox Lifecycle**:
  - `POST /api/users/[userId]/projects/[projectId]/activate` - Create and configure sandbox
  - `POST /api/users/[userId]/projects/[projectId]/deactivate` - Stop and cleanup sandbox  
  - `GET /api/users/[userId]/projects/[projectId]/status` - Get current sandbox status
  - `GET /api/users/[userId]/projects/[projectId]/logs` - Stream sandbox logs via SSE
- **Goose Proxy**:
  - `POST /api/users/[userId]/projects/[projectId]/messages` - Proxy to Goose API in sandbox
  - `GET /api/users/[userId]/projects/[projectId]/sessions` - List Goose sessions

### Data Layer
- **MongoDB Collections**:
  - `projects`: Project metadata, sandbox IDs, status, endpoints, created/updated timestamps
  - `sandbox_logs`: Persistent log storage for debugging and audit (optional)
  - `sessions`: Reuse existing Goose sessions collection for chat persistence

### Vercel Sandbox Integration
- **Sandbox Configuration**:
  ```typescript
  await Sandbox.create({
    teamId: process.env.VERCEL_TEAM_ID,
    projectId: process.env.VERCEL_PROJECT_ID, 
    token: process.env.VERCEL_TOKEN,
    source: {
      type: 'git',
      url: 'https://github.com/your-org/goose-api-container.git', // Or ACR image URL
      revision: 'main'
    },
    resources: { vcpus: 2 },
    timeout: ms('30m'), // 30 minutes for MVP
    ports: [3001], // Goose API port
    runtime: 'node22' // or 'python3.13' depending on Goose API
  })
  ```
- **Lifecycle Management**:
  - Sandbox creation with dependency installation (npm/pip)
  - Goose API server startup and health checks
  - Domain retrieval via `sandbox.domain(3001)`
  - Resource monitoring and automatic cleanup
  - Graceful shutdown with session persistence

## Implementation Steps

### 1. Project Setup and Configuration
```bash
# Initialize Next.js project with TypeScript
npx create-next-app@latest goose-vercel-app --typescript --tailwind --app
cd goose-vercel-app

# Install dependencies
pnpm add @vercel/sandbox @vercel/functions ms
pnpm add mongoose @types/mongoose # MongoDB ODM
pnpm add @tanstack/react-query # Data fetching
pnpm add lucide-react @radix-ui/react-* # UI components
pnpm add -D @types/ms @types/node
```

**Environment Variables**:
```bash
# Vercel Sandbox
VERCEL_TOKEN=vercel_token_here
VERCEL_TEAM_ID=team_id_here  
VERCEL_PROJECT_ID=project_id_here

# MongoDB
MONGODB_URI=mongodb://localhost:27017/goose-vercel

# Optional: Container Registry
AZURE_CONTAINER_REGISTRY_URL=your-registry.azurecr.io
GOOSE_API_IMAGE=your-registry.azurecr.io/goose-api:latest

# Git Repository (alternative to container)
GOOSE_API_REPO_URL=https://github.com/your-org/goose-api.git
```

### 2. Database Schema and Models
```typescript
// lib/db/models.ts
import mongoose from 'mongoose'

const ProjectSchema = new mongoose.Schema({
  _id: { type: String, required: true }, // UUID
  userId: { type: String, required: true, index: true },
  name: { type: String, required: true },
  description: String,
  
  // Sandbox state
  sandboxId: String,
  sandboxStatus: { 
    type: String, 
    enum: ['creating', 'active', 'stopping', 'inactive', 'error'],
    default: 'inactive'
  },
  sandboxDomain: String,
  sandboxCreatedAt: Date,
  sandboxStoppedAt: Date,
  
  // Error handling
  lastError: String,
  retryCount: { type: Number, default: 0 },
  
  // Metadata
  createdAt: { type: Date, default: Date.now },
  updatedAt: { type: Date, default: Date.now }
}, { timestamps: true })

ProjectSchema.index({ userId: 1, name: 1 }, { unique: true })
```

### 3. Sandbox Management Layer
```typescript
// lib/sandbox/manager.ts
import { Sandbox } from '@vercel/sandbox'
import ms from 'ms'

export class SandboxManager {
  async createProjectSandbox(project: Project): Promise<SandboxResult> {
    const config = {
      teamId: process.env.VERCEL_TEAM_ID!,
      projectId: process.env.VERCEL_PROJECT_ID!,
      token: process.env.VERCEL_TOKEN!,
      source: this.getSandboxSource(project),
      resources: { vcpus: 2 },
      timeout: ms('30m'),
      ports: [3001],
      runtime: 'node22' as const
    }

    const sandbox = await Sandbox.create(config)
    
    // Install dependencies and start Goose API
    await this.setupGooseApi(sandbox)
    
    return {
      sandbox,
      domain: sandbox.domain(3001),
      logs: this.extractLogs()
    }
  }

  private getSandboxSource(project: Project) {
    if (process.env.GOOSE_API_REPO_URL) {
      return {
        type: 'git' as const,
        url: process.env.GOOSE_API_REPO_URL,
        revision: 'main'
      }
    }
    
    // Fallback: Create minimal Node.js server with Goose API
    return {
      type: 'tarball' as const,
      url: this.createGooseApiTarball()
    }
  }

  private async setupGooseApi(sandbox: Sandbox) {
    // Install Node.js dependencies
    await sandbox.runCommand({
      cmd: 'npm',
      args: ['install', 'express', '@your-org/goose-api']
    })
    
    // Create and start server
    await sandbox.writeFiles([{
      path: 'server.js',
      content: Buffer.from(this.getGooseServerScript())
    }])
    
    // Start server in background
    await sandbox.runCommand({
      cmd: 'node',
      args: ['server.js'],
      detached: true
    })
    
    // Wait for server to be ready
    await this.waitForHealthCheck(sandbox)
  }
}
```

### 4. API Routes Implementation
```typescript
// app/api/users/[userId]/projects/[projectId]/activate/route.ts
export async function POST(request: Request, { params }: { params: { userId: string, projectId: string } }) {
  try {
    const project = await Project.findOne({ 
      _id: params.projectId, 
      userId: params.userId 
    })
    
    if (!project) {
      return NextResponse.json({ error: 'Project not found' }, { status: 404 })
    }
    
    if (project.sandboxStatus === 'active') {
      return NextResponse.json({ 
        message: 'Project already active',
        domain: project.sandboxDomain 
      })
    }
    
    // Update status to creating
    await Project.updateOne(
      { _id: params.projectId },
      { 
        sandboxStatus: 'creating',
        updatedAt: new Date()
      }
    )
    
    // Create sandbox asynchronously
    const sandboxManager = new SandboxManager()
    const result = await sandboxManager.createProjectSandbox(project)
    
    // Update project with sandbox details
    await Project.updateOne(
      { _id: params.projectId },
      {
        sandboxId: result.sandbox.id,
        sandboxStatus: 'active',
        sandboxDomain: result.domain,
        sandboxCreatedAt: new Date(),
        lastError: null,
        retryCount: 0
      }
    )
    
    return NextResponse.json({
      success: true,
      domain: result.domain,
      status: 'active'
    })
    
  } catch (error) {
    // Update project with error status
    await Project.updateOne(
      { _id: params.projectId },
      {
        sandboxStatus: 'error',
        lastError: error.message,
        retryCount: { $inc: 1 }
      }
    )
    
    return NextResponse.json(
      { error: 'Failed to activate project', details: error.message },
      { status: 500 }
    )
  }
}
```

## Key Architectural Differences from Kubernetes Plan

### Resource Management
- **K8s**: Persistent infrastructure with scaling to zero
- **Vercel**: Ephemeral sandboxes with automatic cleanup

### State Persistence
- **K8s**: Volumes and ConfigMaps for session data
- **Vercel**: MongoDB for all persistent data; sandboxes are stateless

### Networking
- **K8s**: Ingress controllers and internal service discovery
- **Vercel**: Public sandbox domains with built-in SSL

### Cost Model
- **K8s**: Fixed cluster costs + variable compute
- **Vercel**: Usage-based (Active CPU, memory, network, creations)

### Scaling
- **K8s**: Manual cluster management and node scaling
- **Vercel**: Automatic with concurrency limits (10 Hobby, 2000 Pro/Enterprise)

## Operational Considerations

### Cost Management
- **Sandbox Lifecycle**: Implement aggressive cleanup after inactivity (5-10 minutes)
- **Resource Sizing**: Start with 2 vCPUs per sandbox, monitor usage
- **Concurrency Planning**: Track active sandboxes; implement queuing for bursts
- **Usage Monitoring**: Log Active CPU hours, memory usage, bandwidth for billing analysis

### Reliability & Monitoring
- **Health Checks**: Ping Goose API endpoints every 30 seconds
- **Automatic Retries**: Retry sandbox creation up to 3 times with exponential backoff
- **Graceful Degradation**: Show meaningful error messages; allow manual retry
- **Alerting**: Monitor failed activations, high error rates, resource exhaustion

### Security
- **Token Management**: Rotate Vercel tokens regularly; use OIDC when available
- **Network Isolation**: Sandboxes are isolated by default; no additional config needed
- **Data Protection**: Never log sensitive API keys; redact tokens in error messages
- **Access Control**: Backend validates user/project ownership before sandbox operations

## Success Metrics & Next Steps

- **Activation Time**: < 60 seconds from request to active Goose API
- **Reliability**: > 95% successful activations
- **Cost Efficiency**: < $0.50 per hour per active project (estimated)
- **User Experience**: Seamless chat integration with < 2 second response times
- **Concurrency**: Support 10+ simultaneous active projects (within Hobby plan limits)

## Open Questions & Risks

### Technical Risks
1. **Cold Start Performance**: Sandbox creation + dependency installation may exceed 60s target
   - *Mitigation*: Pre-built container images, dependency caching, parallel setup steps
2. **Network Reliability**: Sandbox domains may have variable latency or availability  
   - *Mitigation*: Health checking, request timeouts, fallback error handling
3. **Resource Limits**: Vercel concurrency limits may constrain user experience
   - *Mitigation*: Queue management, user notifications, Pro plan upgrade path

### Operational Risks
1. **Cost Overruns**: Uncontrolled sandbox usage could exceed budget expectations
   - *Mitigation*: Usage alerts, per-user limits, automatic cleanup policies
2. **Debugging Complexity**: Ephemeral environments make troubleshooting harder than K8s
   - *Mitigation*: Comprehensive logging, sandbox replay capabilities, local development parity
3. **Vendor Lock-in**: Heavy dependence on Vercel Sandbox beta features
   - *Mitigation*: Abstract sandbox interface, evaluate alternatives (RunPod, Modal, etc.)

### Product Decisions Needed
1. **Goose API Packaging**: Container image vs Git repository deployment strategy?
2. **Session Persistence**: How to handle active chat sessions during sandbox restarts?
3. **Multi-tenancy**: Should projects share sandboxes or remain strictly isolated?
4. **Authentication**: When to add real user auth vs continuing with static user list?

## Next Steps for Implementation

1. **Week 1**: Project setup, basic Next.js structure, MongoDB integration
2. **Week 2**: Vercel Sandbox integration, basic activation/deactivation flow
3. **Week 3**: Goose API proxy, chat interface, real-time status updates
4. **Week 4**: Error handling, monitoring, basic cost controls
5. **Week 5**: Testing, documentation, demo preparation
