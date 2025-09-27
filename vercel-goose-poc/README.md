# Kubernetes Goose POC

A proof-of-concept web application that demonstrates using Kubernetes to run isolated Goose API instances per project. This is a comparison alternative to the Vercel Sandbox approach.

## Features

- **User Management**: Select from predefined users
- **Project CRUD**: Create, list, and delete projects per user
- **Kubernetes Integration**: Deploy Goose API to isolated K8s namespaces
- **Lifecycle Management**: Activate/deactivate projects by scaling deployments
- **Chat Interface**: Send messages to Goose API running in Kubernetes pods
- **Real-time Status**: View project activation status with detailed logs

## Architecture

### Kubernetes Resources per Project
- **Namespace**: `user-{userId}` (shared by user's projects)
- **Deployment**: `proj-{projectId}-api` with Goose API container
- **Service**: `proj-{projectId}-svc` (LoadBalancer type for external access)
- **Ingress**: `proj-{projectId}-ingress` (optional, if base domain configured)

### Scaling Strategy
- **Inactive**: Deployment scaled to 0 replicas (no pods running)
- **Active**: Deployment scaled to 1 replica (pod running and ready)
- **Cost**: Only pay for active compute resources

## Setup

### 1. Prerequisites

- **Kubernetes Cluster**: AKS, EKS, GKE, or local (minikube/kind)
- **kubectl**: Configured with cluster access
- **MongoDB**: Running locally or cloud instance
- **Container Image**: Goose API image in Azure Container Registry

### 2. Install Dependencies

```bash
cd vercel-goose-poc
npm install
```

### 3. Environment Variables

Copy `.env.example` to `.env.local` and configure:

```bash
cp .env.example .env.local
```

**Required variables:**
```bash
# MongoDB
MONGODB_URI=mongodb://localhost:27017/goose-k8s-poc
MONGODB_DB=goose

# Kubernetes Authentication (choose one method)
# Method 1: Base64 encoded kubeconfig
KUBE_CONFIG_BASE64=<base64_encoded_kubeconfig>

# Method 2: Discrete credentials
KUBE_HOST=https://your-cluster.hcp.region.azmk8s.io:443
KUBE_TOKEN=your_service_account_token
KUBE_CA=your_ca_certificate

# Container Image
ACR_IMAGE=myregistry.azurecr.io/goose-api:latest

# Optional Configuration
KUBE_NAMESPACE_PREFIX=user-
INGRESS_BASE_DOMAIN=example.com
GOOSE_API_PORT=3001
```

### 4. Kubernetes RBAC Setup

Your kubeconfig/token needs permissions to:
- Create/delete namespaces
- Create/delete/patch deployments, services, ingresses
- List pods and check status

Example ServiceAccount permissions:
```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: goose-poc-manager
rules:
- apiGroups: [""]
  resources: ["namespaces", "services", "pods"]
  verbs: ["create", "delete", "get", "list", "patch", "update"]
- apiGroups: ["apps"]
  resources: ["deployments"]
  verbs: ["create", "delete", "get", "list", "patch", "update"]
- apiGroups: ["networking.k8s.io"]
  resources: ["ingresses"]
  verbs: ["create", "delete", "get", "list", "patch", "update"]
```

### 5. Run Development Server

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

## How It Works

1. **Select User**: Choose from predefined users (Alice, Bob, Carol)
2. **Create Project**: Add a new project - this creates K8s manifests but doesn't start pods
3. **Activate Project**: 
   - Creates namespace (if first project for user)
   - Applies Deployment, Service, Ingress manifests
   - Scales deployment to 1 replica
   - Waits for pod to be ready
   - Returns external endpoint (LoadBalancer IP or Ingress hostname)
4. **Chat**: Send messages to the Goose API running in the Kubernetes pod
5. **Deactivate**: Scale deployment to 0 (stops pod, saves costs)
6. **Delete**: Remove all Kubernetes resources and database record

## API Endpoints

- `GET /api/users` - List all users
- `GET /api/users/[userId]/projects` - List user's projects
- `POST /api/users/[userId]/projects` - Create new project (with K8s manifests)
- `DELETE /api/users/[userId]/projects/[projectId]` - Delete project and K8s resources
- `POST /api/users/[userId]/projects/[projectId]/activate` - Scale up deployment
- `POST /api/users/[userId]/projects/[projectId]/deactivate` - Scale down deployment
- `POST /api/users/[userId]/projects/[projectId]/messages` - Proxy to Goose API

## Kubernetes vs Vercel Sandbox Comparison

### Kubernetes Approach (This POC)
✅ **Infrastructure Control**: Full control over compute, networking, storage
✅ **Cost Efficiency**: Pay only for running pods (can scale to 0)
✅ **Flexibility**: Support any container image, custom networking policies
✅ **Persistence**: Persistent volumes for data, configurable resource limits
✅ **Production Ready**: Battle-tested orchestration for real workloads

❌ **Complexity**: Requires K8s cluster management and expertise
❌ **Setup Time**: Slower initial deployment (image pull, pod startup)
❌ **Maintenance**: Need to manage cluster updates, security patches

### Vercel Sandbox Approach
✅ **Simplicity**: Managed service, no infrastructure concerns
✅ **Speed**: Fast cold starts, optimized for ephemeral compute
✅ **Developer Experience**: Built-in logging, domains, easy integration

❌ **Limited Control**: Fixed runtime environments, network restrictions
❌ **Cost Model**: Usage-based billing, potential cost spikes
❌ **Vendor Lock-in**: Depends on Vercel's roadmap and pricing

## Troubleshooting

### Common Issues

1. **"Kubernetes client initialization failed"**
   - Check your `KUBE_CONFIG_BASE64` or discrete K8s credentials
   - Verify cluster connectivity: `kubectl cluster-info`

2. **"Pod failed to become ready within timeout"**
   - Check if your `ACR_IMAGE` exists and is accessible
   - Verify the image has a health endpoint at `/health`
   - Check pod logs: `kubectl logs -n user-{userId} deployment/proj-{projectId}-api`

3. **"No external endpoint found"**
   - LoadBalancer service may take time to get external IP
   - Check service status: `kubectl get svc -n user-{userId}`
   - Consider using port-forward for testing: `kubectl port-forward -n user-{userId} svc/proj-{projectId}-svc 3001:3001`

4. **"Failed to create namespace"**
   - Check RBAC permissions for your service account
   - Verify cluster has available resources

### Development Tips

- **Local Testing**: Use `minikube` or `kind` for local Kubernetes development
- **Image Testing**: Test your Goose API image separately: `docker run -p 3001:3001 your-image`
- **Resource Monitoring**: Watch pod status: `kubectl get pods -n user-{userId} -w`
- **Debugging**: Check events: `kubectl describe pod -n user-{userId} -l app=proj-{projectId}-api`

## Next Steps

For production deployment:
- Implement proper authentication and RBAC
- Add resource quotas and limits per namespace
- Set up monitoring and alerting (Prometheus/Grafana)
- Implement GitOps for deployment automation
- Add persistent volumes for Goose session data
- Configure ingress with TLS certificates
- Implement auto-scaling based on usage
