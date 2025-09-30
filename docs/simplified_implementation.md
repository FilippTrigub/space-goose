# Simplified GitHub Repository Cloning Implementation

## Implementation Summary

I've implemented the simpler approach you requested:

### ✅ **Approach Implemented**

1. **Start pod as before** - No init containers, standard deployment
2. **Wait for health endpoint** - `/api/v1/health` returns 200
3. **Execute clone command on pod** - Using `kubernetes.stream` to run git commands
4. **Error handling** - Throw alerts if cloning fails

## 🔧 **Key Functions Added**

### **1. Health Check with Retry** (`wait_for_pod_health`)
```python
async def wait_for_pod_health(user_id: str, project_id: str, timeout_seconds: int = 120):
    # Polls /api/v1/health endpoint until 200 response
    # 5-second retry intervals, 2-minute timeout
```

### **2. Pod Name Discovery** (`get_pod_name`)
```python
def get_pod_name(user_id: str, project_id: str):
    # Finds running pod by deployment label selector
    # Returns first running pod name
```

### **3. Git Clone Execution** (`execute_git_clone`)
```python
def execute_git_clone(user_id: str, project_id: str, repo_url: str):
    # Uses kubernetes.stream to execute git commands
    # Handles authentication with GitHub PAT
    # Creates /home/goose/workspace/repo directory
```

### **4. Complete Clone Flow** (`clone_repository_on_pod`)
```python
async def clone_repository_on_pod(user_id: str, project_id: str, repo_url: str):
    # Step 1: Wait for pod health
    # Step 2: Execute git clone
    # Comprehensive error handling
```

## 🚀 **Updated Workflows**

### **Project Creation**
- Creates pod normally
- Waits for health endpoint
- If `repo_url` provided, clones repository
- Non-blocking (project succeeds even if clone fails)

### **Project Activation**  
- Scales up deployment
- Waits for health endpoint
- If `repo_url` configured, clones repository
- Graceful error handling

### **Manual Clone Endpoint**
- New `/clone-repository` endpoint for manual cloning
- Can be used to retry failed clones
- Useful for testing and troubleshooting

## 💡 **Key Benefits**

- ✅ **Simple and reliable** - No complex init containers
- ✅ **Uses existing pod** - Leverages running container 
- ✅ **Proper error handling** - Clear failure messages
- ✅ **Non-blocking** - Project works even if clone fails
- ✅ **Leverages existing auth** - Uses GitHub PAT secrets
- ✅ **Manual retry option** - Clone endpoint for manual execution

## 📁 **Files Updated**

- ✅ `k8s_service.py` - Added health check and clone functions
- ✅ `routes/project_routes.py` - Updated create/activate workflows  
- ✅ `models.py` - Repository URL fields (kept from before)
- ✅ `templates/index.html` - Repository URL input (kept from before)

## 🎯 **Usage Flow**

1. User creates project with repository URL
2. Pod starts normally
3. Health endpoint monitored until ready
4. Git clone executed on healthy pod
5. Repository available in `/home/goose/workspace/repo`
6. Sessions can access repository files

The implementation is **much simpler** while maintaining all the functionality. Ready for testing!