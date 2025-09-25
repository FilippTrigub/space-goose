# K8s Environment Manager

A proof-of-concept web application for managing Kubernetes-isolated user environments. This application allows operators to:

- Select users from a dropdown
- Create, update, and delete projects
- Activate/deactivate isolated K8s environments per project
- Send messages to Goose API endpoints in active environments

## Architecture

### Backend (FastAPI)
- **Models**: Pydantic models for request/response validation
- **Routes**: RESTful API endpoints for project management
- **Services**: 
  - MongoDB service for project persistence
  - Kubernetes service for cluster resource management
- **Features**: SSE streaming for real-time message proxy

### Frontend (Vanilla JS + HTML/CSS)
- Clean, minimal UI with modern styling
- Real-time project status updates
- Interactive message interface
- Responsive design

### Infrastructure
- **Database**: MongoDB for project metadata
- **Orchestration**: Kubernetes for isolated environments
- **Container Registry**: Azure Container Registry (ACR) for Goose API images

## Key Features Implemented

✓ **User Management**: Static user list for MVP  
✓ **Project CRUD**: Create, read, update, delete operations  
✓ **Environment Lifecycle**: Activate/deactivate K8s deployments  
✓ **Resource Management**: Automatic namespace, deployment, service creation  
✓ **Message Proxy**: SSE streaming to Goose API endpoints  
✓ **Mock Mode**: Graceful degradation when K8s/MongoDB unavailable  
✓ **Error Handling**: Comprehensive error reporting and rollback  
✓ **Clean UI**: Modern, responsive interface with status indicators  

## Project Structure

```
k8s-manager/
├── main.py              # FastAPI application entry point
├── models.py            # Pydantic models for data validation
├── requirements.txt     # Python dependencies
├── Dockerfile          # Container build configuration
├── routes/
│   └── project_routes.py # API endpoints for project management
├── services/
│   ├── mongodb_service.py # MongoDB operations
│   └── k8s_service.py    # Kubernetes cluster operations
└── templates/
    └── index.html       # Frontend UI
```

## API Endpoints

- `GET /users` - List available users
- `GET /users/{user_id}/projects` - Get user's projects
- `POST /users/{user_id}/projects` - Create new project
- `PUT /users/{user_id}/projects/{project_id}` - Update project
- `DELETE /users/{user_id}/projects/{project_id}` - Delete project
- `POST /users/{user_id}/projects/{project_id}/activate` - Activate environment
- `POST /users/{user_id}/projects/{project_id}/deactivate` - Deactivate environment
- `POST /users/{user_id}/projects/{project_id}/messages` - Proxy messages to Goose API

## Setup Instructions

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment**:
   ```bash
   export MONGO_URI="mongodb://localhost:27017/"
   export MONGO_DB="k8s_manager"
   export ACR_IMAGE="your-registry.azurecr.io/goose-api:latest"
   export KUBECONFIG="/path/to/your/kubeconfig"
   ```

3. **Start MongoDB**:
   ```bash
   mongod  # or use MongoDB Atlas
   ```

4. **Run Application**:
   ```bash
   python main.py
   ```

5. **Access UI**: Open http://localhost:8000

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MONGO_URI` | `mongodb://localhost:27017/` | MongoDB connection string |
| `MONGO_DB` | `k8s_manager` | Database name |
| `ACR_IMAGE` | `your-acr-repo/goose-api:latest` | Container image for projects |
| `KUBECONFIG` | System default | Path to Kubernetes config |

## Kubernetes Resources Created

For each project, the following resources are created:

- **Namespace**: `user-{user_id}` (shared across user's projects)
- **Deployment**: `proj-{project_id}-api` (Goose API container)
- **Service**: `proj-{project_id}-api` (ClusterIP, port 80 → 3001)
- **Environment Variables**: `USER_ID`, `PROJECT_ID` passed to containers

## Development Notes

- **Mock Mode**: Application runs without K8s/MongoDB for development
- **Security**: No authentication/authorization (PoC scope)
- **Testing**: No formal tests (PoC scope)
- **Resilience**: Basic error handling, no advanced recovery mechanisms
- **Scalability**: Designed for MVP/demo usage

## Usage Flow

1. Select a user from the dropdown
2. Create a new project with a descriptive name
3. Click "Activate" to deploy the K8s environment
4. Click "Messages" to connect to the project's chat interface
5. Send messages to interact with the Goose API
6. "Deactivate" to scale down resources when done
7. "Delete" to remove the project entirely

## UI Features

- 🟢 **Active Status**: Green badge for running projects
- 🔴 **Inactive Status**: Red badge for stopped projects
- **Real-time Updates**: Automatic UI refresh after operations
- **Error Handling**: User-friendly error messages
- **Streaming Messages**: Live SSE feed from Goose API
- **Responsive Design**: Works on desktop and mobile

This implementation follows the MVP specification while providing a clean, functional interface for managing Kubernetes-based AI environments.

## Kubernetes Configuration Fix

The application now properly handles different Kubernetes connection scenarios:

### Connection Modes

1. **In-Cluster Mode**: When running inside a Kubernetes pod
2. **Kubeconfig Mode**: When running locally with kubeconfig file
3. **Mock Mode**: When no Kubernetes connectivity is available (development)

### Configuration Priority

The app tries to connect to Kubernetes in this order:
1. In-cluster config (if `KUBERNETES_SERVICE_HOST` is set)
2. Default kubeconfig (`~/.kube/config`)
3. Custom kubeconfig (if `KUBECONFIG` env var is set)
4. Falls back to mock mode if none work

### Quick Start

```bash
# Clone and navigate to the project
cd k8s-manager

# Quick start with auto-setup
./start.sh

# OR manual setup:
pip install -r requirements.txt
python main.py
```

### Environment Setup

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your settings
vim .env
```

### Health Check

Once running, check the system status:
- **UI**: http://localhost:8000
- **Health**: http://localhost:8000/health
- **API Status**: http://localhost:8000/api/status

### Mock Mode vs Production Mode

**Mock Mode** (Development):
- No actual Kubernetes resources created
- All operations logged but not executed
- Perfect for UI development and testing
- No external dependencies required

**Production Mode** (Kubernetes Available):
- Real Kubernetes resources created/managed
- Actual pod deployments and services
- Requires valid kubeconfig or in-cluster permissions

### Troubleshooting Kubernetes Connection

If you see the error:
```
kubernetes.config.config_exception.ConfigException: Service host/port is not set.
```

This means:
1. You're running outside a Kubernetes cluster
2. No valid kubeconfig file was found
3. The app automatically falls back to mock mode

**To fix:**
```bash
# Option 1: Set kubeconfig path
export KUBECONFIG=/path/to/your/kubeconfig

# Option 2: Copy kubeconfig to default location
cp /path/to/your/kubeconfig ~/.kube/config

# Option 3: Run in mock mode (no action needed)
# The app will work fine without Kubernetes
```

The application is designed to be **graceful** - it works perfectly in mock mode for development and automatically enables full functionality when Kubernetes is available.

## Updated Kubernetes Configuration

### Base64 Kubeconfig Support

The application now supports base64-encoded kubeconfig for secure deployment without storing config files in repositories.

#### Configuration Priority (in order):

1. **Base64-encoded config** (recommended for deployment)
   ```bash
   export KUBECONFIG_BASE64="<base64-encoded-kubeconfig>"
   ```

2. **Custom kubeconfig path**
   ```bash
   export KUBECONFIG="/path/to/your/kubeconfig"
   ```

3. **Default location** (`~/.kube/config`)
   - No environment variable needed

4. **In-cluster config** (when running inside Kubernetes)
   - Automatic detection

#### Converting Kubeconfig to Base64

```bash
# Convert your kubeconfig to base64
cat ~/.kube/config | base64 -w 0

# Copy the output and set as environment variable
export KUBECONFIG_BASE64="LS0tLS1CRUdJTi..."

# Or add to .env file
echo "KUBECONFIG_BASE64=LS0tLS1CRUdJTi..." >> .env
```

#### Benefits of Base64 Approach

- **Security**: No kubeconfig files in repository
- **Deployment**: Easy to set as environment variable in CI/CD
- **Portability**: Works across different environments
- **Clean**: No temporary files or paths to manage

#### Error Handling

The application now **fails fast** if no valid Kubernetes configuration is found. This ensures:
- Clear error messages about missing configuration
- No silent failures or mock mode confusion
- Explicit configuration requirements

If you see startup errors, ensure one of the configuration methods above is properly set.
