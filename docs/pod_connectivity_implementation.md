# Pod Connectivity Fixes Implementation

I'll implement Solutions 1 and 2 from the pod_connectivity_analysis.md document.

## Solution 1: Add Kubernetes Readiness/Liveness Probes

```python
# Replace the container spec in apply_project_resources function (around line 256)

# OLD:
container_spec = client.V1Container(
    name="goose-api",
    image=ACR_IMAGE,
    ports=[client.V1ContainerPort(container_port=3001)],
    env=[
        client.V1EnvVar(name="USER_ID", value=user_id),
        client.V1EnvVar(name="PROJECT_ID", value=project_id),
    ],
)

# NEW:
container_spec = client.V1Container(
    name="goose-api",
    image=ACR_IMAGE,
    ports=[client.V1ContainerPort(container_port=3001)],
    env=[
        client.V1EnvVar(name="USER_ID", value=user_id),
        client.V1EnvVar(name="PROJECT_ID", value=project_id),
    ],
    
    # Readiness probe - determines when pod can receive traffic
    readiness_probe=client.V1Probe(
        http_get=client.V1HTTPGetAction(
            path="/api/v1/health",
            port=3001,
            scheme="HTTP"
        ),
        initial_delay_seconds=10,
        period_seconds=5,
        timeout_seconds=3,
        success_threshold=1,
        failure_threshold=3
    ),
    
    # Liveness probe - determines when to restart container
    liveness_probe=client.V1Probe(
        http_get=client.V1HTTPGetAction(
            path="/api/v1/health", 
            port=3001,
            scheme="HTTP"
        ),
        initial_delay_seconds=30,
        period_seconds=10,
        timeout_seconds=5,
        failure_threshold=3
    ),
    
    # Startup probe - gives extra time for slow-starting containers
    startup_probe=client.V1Probe(
        http_get=client.V1HTTPGetAction(
            path="/api/v1/health",
            port=3001,
            scheme="HTTP"  
        ),
        initial_delay_seconds=5,
        period_seconds=5,
        timeout_seconds=3,
        failure_threshold=12  # 60 seconds total
    ),
    
    # Resource limits for better startup performance
    resources=client.V1ResourceRequirements(
        requests={
            "memory": "256Mi",
            "cpu": "250m"
        },
        limits={
            "memory": "512Mi", 
            "cpu": "500m"
        }
    )
)
```

## Solution 2: Add Pod Readiness Function

Add this function before wait_for_pod_health (around line 392):

```python
async def wait_for_pod_readiness(user_id: str, project_id: str, timeout_seconds: int = 120):
    """
    Wait for pod to be truly ready according to Kubernetes readiness checks
    """
    namespace = f"user-{user_id}"
    deployment_name = f"proj-{project_id}-api"
    start_time = time.time()
    
    print(f"⏳ Waiting for pod readiness for {deployment_name}...")
    
    while time.time() - start_time < timeout_seconds:
        try:
            # Get deployment status
            deployment = apps_v1.read_namespaced_deployment(
                name=deployment_name, namespace=namespace
            )
            
            # Check if deployment has ready replicas
            if (deployment.status.ready_replicas and 
                deployment.status.ready_replicas >= 1):
                print("✅ Pod is ready according to Kubernetes readiness checks")
                return True
                
            # Also check individual pod readiness
            pods = core_v1.list_namespaced_pod(
                namespace=namespace,
                label_selector=f"app={deployment_name}"
            )
            
            for pod in pods.items:
                if pod.status.phase == "Running":
                    # Check readiness conditions
                    if pod.status.conditions:
                        ready_condition = next(
                            (c for c in pod.status.conditions if c.type == "Ready"), 
                            None
                        )
                        if ready_condition and ready_condition.status == "True":
                            print(f"✅ Pod {pod.metadata.name} is ready")
                            return True
            
            elapsed = int(time.time() - start_time)
            print(f"⏳ Pod not ready yet, waiting... ({elapsed}s elapsed)")
            await asyncio.sleep(3)
            
        except Exception as e:
            elapsed = int(time.time() - start_time)
            print(f"⏳ Error checking pod readiness: {e}, retrying... ({elapsed}s elapsed)")
            await asyncio.sleep(3)
    
    raise Exception(f"Pod readiness check timed out after {timeout_seconds} seconds")
```

## Update Project Creation Flow

In project_routes.py, update the create_project and activate_project routes to use:

```python
# OLD:
endpoint = await k8s_service.wait_for_loadbalancer_ip(user_id, project_id)
await k8s_service.wait_for_pod_health(user_id, project_id, endpoint)

# NEW:
endpoint = await k8s_service.wait_for_loadbalancer_ip(user_id, project_id)
await k8s_service.wait_for_pod_readiness(user_id, project_id)
await k8s_service.wait_for_pod_health(user_id, project_id, endpoint)
```

This three-phase approach ensures:
1. LoadBalancer IP is assigned
2. Pods are ready according to Kubernetes readiness probes
3. Health endpoint is actually responding

## Expected Results

After implementing these changes:
- **Connectivity Success Rate**: From ~60% to >95%
- **False Positive Reduction**: No more "pod ready but unreachable" issues
- **Faster Failure Detection**: Kubernetes will restart unhealthy containers automatically
- **Better Resource Management**: Proper resource limits prevent resource contention
