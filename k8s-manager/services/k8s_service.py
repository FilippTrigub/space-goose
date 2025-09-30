import os
import base64
import tempfile
import time
import httpx
import asyncio
from kubernetes import client, config
from kubernetes.client.rest import ApiException
from kubernetes.config.config_exception import ConfigException
from kubernetes.stream import stream

ACR_IMAGE = os.getenv("ACR_IMAGE")
KUBE_CONFIG = os.getenv("KUBECONFIG")
KUBE_CONFIG_BASE64 = os.getenv("KUBECONFIG_BASE64")


def load_k8s_config():
    """
    Load Kubernetes configuration with support for base64-encoded config.
    Returns True if successful, False if no valid config found.
    """
    # Try base64-encoded config first (preferred for deployment)
    if KUBE_CONFIG_BASE64:
        try:
            print("Trying base64-encoded kubeconfig...")
            # Decode base64 config
            config_data = base64.b64decode(KUBE_CONFIG_BASE64).decode("utf-8")

            # Create temporary file with the decoded config
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".yaml", delete=False
            ) as temp_file:
                temp_file.write(config_data)
                temp_config_path = temp_file.name

            # Load config from temporary file
            config.load_kube_config(config_file=temp_config_path)

            # Clean up temporary file
            os.unlink(temp_config_path)

            print("✓ Successfully loaded base64-encoded kubeconfig")
            return True
        except Exception as e:
            print(f"Base64 kubeconfig loading failed: {e}")
            # Fall through to try other methods

    # Try custom kubeconfig path if set
    if KUBE_CONFIG:
        try:
            print(f"Trying custom kubeconfig path: {KUBE_CONFIG}")
            config.load_kube_config(config_file=KUBE_CONFIG)
            print("✓ Successfully loaded custom kubeconfig")
            return True
        except Exception as e:
            print(f"Custom kubeconfig loading failed: {e}")

    # Try default kubeconfig location
    try:
        print("Attempting to load kubeconfig from default location (~/.kube/config)...")
        config.load_kube_config()
        print("✓ Successfully loaded default kubeconfig")
        return True
    except Exception as e:
        print(f"Default kubeconfig loading failed: {e}")

    # Try in-cluster config as last resort
    try:
        if os.getenv("KUBERNETES_SERVICE_HOST"):
            print("Trying in-cluster config...")
            config.load_incluster_config()
            print("✓ Successfully loaded in-cluster config")
            return True
    except Exception as e:
        print(f"In-cluster config failed: {e}")

    print("⚠ No valid Kubernetes configuration found.")
    print("To enable Kubernetes functionality:")
    print(
        "1. Set KUBECONFIG_BASE64 environment variable with base64-encoded kubeconfig"
    )
    print("2. Or set KUBECONFIG environment variable to your kubeconfig file path")
    print("3. Or run inside a Kubernetes cluster with proper service account")
    print("4. Or ensure ~/.kube/config exists and is valid")
    return False


# Try to load config, fail hard if not available
k8s_available = load_k8s_config()

if not k8s_available:
    raise Exception(
        "Kubernetes configuration not found or invalid. Application cannot start without K8s access."
    )

# Initialize Kubernetes clients
api_client = client.ApiClient()
core_v1 = client.CoreV1Api()
apps_v1 = client.AppsV1Api()
networking_v1 = client.NetworkingV1Api()

# Test the connection
try:
    version = core_v1.get_api_resources()
    print("✓ Kubernetes API connection verified")
except Exception as e:
    print(f"⚠ Kubernetes API connection failed: {e}")
    raise Exception(f"Kubernetes API connection failed: {e}")


def ensure_namespace(user_id: str):
    """
    Ensure namespace exists for the given user.
    """
    namespace = f"user-{user_id}"

    try:
        # Check if namespace already exists
        core_v1.read_namespace(name=namespace)
        print(f"✓ Namespace {namespace} already exists")
    except ApiException as e:
        if e.status == 404:
            # Namespace doesn't exist, create it
            try:
                namespace_obj = client.V1Namespace(
                    metadata=client.V1ObjectMeta(
                        name=namespace,
                        labels={"managed-by": "k8s-manager", "user-id": user_id},
                        annotations={
                            "description": f"Namespace for user {user_id} projects"
                        },
                    )
                )
                core_v1.create_namespace(body=namespace_obj)
                print(f"✓ Created namespace: {namespace}")
            except Exception as create_error:
                print(f"✗ Failed to create namespace {namespace}: {create_error}")
                raise create_error
        else:
            print(f"✗ Failed to check namespace {namespace}: {e}")
            raise e
    except Exception as e:
        print(f"✗ Unexpected error with namespace {namespace}: {e}")
        raise e

    return namespace


def apply_project_resources(
    user_id: str,
    project_id: str,
    github_key: str = None,
    user_secret_exists: bool = False,
):
    """
    Create Kubernetes resources for a project with enhanced health checks.
    """
    namespace = ensure_namespace(user_id)
    deployment_name = f"proj-{project_id}-api"
    service_name = f"proj-{project_id}-api"

    config_map_name = f"{user_id}-env"
    config_map_exists = False

    source_namespace = "testuser"
    source_config_name = "testuser-env"
    try:
        source_config = core_v1.read_namespaced_config_map(
            name=source_config_name, namespace=source_namespace
        )
        print(
            f"✓ Retrieved source ConfigMap {source_config_name} from namespace {source_namespace}"
        )
        config_map_body = client.V1ConfigMap(
            metadata=client.V1ObjectMeta(
                name=config_map_name,
                labels={
                    "managed-by": "k8s-manager",
                    "user-id": user_id,
                    "project-id": project_id,
                },
            ),
            data=source_config.data,
        )

        try:
            core_v1.create_namespaced_config_map(
                namespace=namespace, body=config_map_body
            )
            print(f"✓ Created ConfigMap {config_map_name} in namespace {namespace}")
            config_map_exists = True
        except ApiException as e:
            if e.status == 409:
                print(
                    f"ℹ ConfigMap {config_map_name} already exists in namespace {namespace}"
                )
                config_map_exists = True
            else:
                print(f"✗ Failed to create ConfigMap: {e}")
                raise e
    except ApiException as e:
        if e.status == 404:
            print(
                f"⚠ Source ConfigMap {source_config_name} not found in namespace {source_namespace}"
            )
            print("Proceeding without ConfigMap...")
        else:
            print(f"✗ Failed to retrieve source ConfigMap: {e}")
            raise e
    except Exception as e:
        print(f"✗ Unexpected error retrieving ConfigMap: {e}")
        raise e

    # Create GitHub Key Secret if provided
    github_secret_name = None
    if user_secret_exists:
        github_secret_name = f"user-user2-github-key"
    if github_key:
        github_secret_name = f"proj-{project_id}-github-key"
        try:
            # Check if secret already exists
            core_v1.read_namespaced_secret(name=github_secret_name, namespace=namespace)
            print(
                f"ℹ GitHub Secret {github_secret_name} already exists in namespace {namespace}"
            )
        except ApiException as e:
            if e.status == 404:
                # Secret doesn't exist, create it
                secret_data = {
                    "GITHUB_PERSONAL_ACCESS_TOKEN": base64.b64encode(
                        github_key.encode("utf-8")
                    ).decode("utf-8")
                }
                secret_body = client.V1Secret(
                    metadata=client.V1ObjectMeta(
                        name=github_secret_name,
                        labels={
                            "managed-by": "k8s-manager",
                            "user-id": user_id,
                            "project-id": project_id,
                        },
                    ),
                    type="Opaque",
                    data=secret_data,
                )
                core_v1.create_namespaced_secret(namespace=namespace, body=secret_body)
                print(
                    f"✓ Created GitHub Secret {github_secret_name} in namespace {namespace}"
                )
            else:
                print(f"✗ Failed to check GitHub Secret: {e}")
                raise e
        except Exception as e:
            print(f"✗ Unexpected error with GitHub Secret: {e}")
            raise e

    try:
        # Create Deployment with enhanced health probes
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
                    "memory": "1024Mi",
                    "cpu": "1000m"
                },
                limits={
                    "memory": "2048Mi", 
                    "cpu": "2000m"
                }
            )
        )

        # Add ConfigMap environment variables if available
        env_from_sources = []
        if config_map_exists:
            env_from_sources.append(
                client.V1EnvFromSource(
                    config_map_ref=client.V1ConfigMapEnvSource(name=config_map_name)
                )
            )

        # Add GitHub Secret environment variables if available
        if github_secret_name:
            print(f"using gh secret name: {github_secret_name}")
            env_from_sources.append(
                client.V1EnvFromSource(
                    secret_ref=client.V1SecretEnvSource(name=github_secret_name)
                )
            )

        if env_from_sources:
            container_spec.env_from = env_from_sources

        print(f"setting env from: {container_spec.env_from}")
        deployment = client.V1Deployment(
            metadata=client.V1ObjectMeta(
                name=deployment_name,
                namespace=namespace,
                labels={
                    "app": deployment_name,
                    "project-id": project_id,
                    "user-id": user_id,
                    "managed-by": "k8s-manager",
                },
            ),
            spec=client.V1DeploymentSpec(
                replicas=1,  # Start active
                selector=client.V1LabelSelector(match_labels={"app": deployment_name}),
                template=client.V1PodTemplateSpec(
                    metadata=client.V1ObjectMeta(
                        labels={
                            "app": deployment_name,
                            "project-id": project_id,
                            "user-id": user_id,
                        }
                    ),
                    spec=client.V1PodSpec(containers=[container_spec]),
                ),
            ),
        )

        try:
            apps_v1.create_namespaced_deployment(namespace=namespace, body=deployment)
            print(f"✓ Created deployment: {deployment_name} with health probes")
        except ApiException as e:
            if e.status == 409:  # Already exists
                print(f"ℹ Deployment {deployment_name} already exists")
            else:
                raise e

        # Create Service with LoadBalancer type and health check annotations
        service = client.V1Service(
            metadata=client.V1ObjectMeta(
                name=service_name,
                namespace=namespace,
                labels={
                    "app": deployment_name,
                    "project-id": project_id,
                    "user-id": user_id,
                    "managed-by": "k8s-manager",
                },
                annotations={
                    # Cloud provider health check configurations
                    "service.beta.kubernetes.io/aws-load-balancer-healthcheck-path": "/api/v1/health",
                    "service.beta.kubernetes.io/aws-load-balancer-healthcheck-port": "3001",
                    "service.beta.kubernetes.io/aws-load-balancer-healthcheck-protocol": "HTTP",
                    "service.beta.kubernetes.io/azure-load-balancer-health-probe-path": "/api/v1/health",
                }
            ),
            spec=client.V1ServiceSpec(
                selector={"app": deployment_name},
                ports=[
                    client.V1ServicePort(
                        port=80, target_port=3001, protocol="TCP", name="http"
                    )
                ],
                type="LoadBalancer",
            ),
        )

        try:
            core_v1.create_namespaced_service(namespace=namespace, body=service)
            print(f"✓ Created service: {service_name} with health check annotations")
        except ApiException as e:
            if e.status == 409:  # Already exists
                print(f"ℹ Service {service_name} already exists")
            else:
                raise e

    except Exception as e:
        print(f"✗ Failed to create resources for project {project_id}: {e}")
        raise e


async def wait_for_loadbalancer_ip(
    user_id: str, project_id: str, timeout_seconds: int = 120
):
    """
    Wait specifically for LoadBalancer IP assignment.
    Separate from pod health - this is infrastructure-level waiting.
    """
    namespace = f"user-{user_id}"
    service_name = f"proj-{project_id}-api"
    start_time = time.time()

    print(f"⏳ Waiting for LoadBalancer IP assignment for {service_name}...")

    while time.time() - start_time < timeout_seconds:
        try:
            service = core_v1.read_namespaced_service(
                name=service_name, namespace=namespace
            )

            # Check if LoadBalancer has been assigned
            if (
                service.status
                and service.status.load_balancer
                and service.status.load_balancer.ingress
                and len(service.status.load_balancer.ingress) > 0
            ):

                ingress = service.status.load_balancer.ingress[0]
                if ingress.ip:
                    print(f"✅ LoadBalancer IP assigned: {ingress.ip}")
                    return ingress.ip
                elif ingress.hostname:
                    print(f"✅ LoadBalancer hostname assigned: {ingress.hostname}")
                    return ingress.hostname

        except ApiException as e:
            if e.status == 404:
                print(f"⏳ Service {service_name} not found, waiting...")
            else:
                print(f"⏳ Error checking service: {e}")

        elapsed = int(time.time() - start_time)
        print(f"⏳ LoadBalancer IP not ready yet, waiting... ({elapsed}s elapsed)")
        await asyncio.sleep(3)  # Check every 10 seconds for infrastructure

    raise Exception(
        f"LoadBalancer IP assignment timed out after {timeout_seconds} seconds"
    )


async def wait_for_pod_readiness(user_id: str, project_id: str, timeout_seconds: int = 300):
    """
    Wait for pod to be truly ready according to Kubernetes readiness checks.
    This ensures the pod passes its readiness probe before we try to connect.
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


async def wait_for_pod_health(
    user_id: str, project_id: str, endpoint: str, timeout_seconds: int = 300
):
    """
    Wait for pod health endpoint to return 200.
    Assumes endpoint is already available (from LoadBalancer) and pod is ready.
    """
    start_time = time.time()

    print(f"⏳ Waiting for pod health at {endpoint}...")

    while time.time() - start_time < timeout_seconds:
        try:
            async with httpx.AsyncClient(
                timeout=6.0
            ) as client:  # Longer timeout for startup
                health_url = f"http://{endpoint}/api/v1/health"
                response = await client.get(health_url)

                if response.status_code == 200:
                    print(
                        f"✅ Pod is healthy! Health endpoint responding at: {health_url}"
                    )
                    return True
                else:
                    elapsed = int(time.time() - start_time)
                    print(
                        f"⏳ Health check returned {response.status_code}, retrying... ({elapsed}s elapsed)"
                    )

        except Exception as e:
            elapsed = int(time.time() - start_time)
            print(f"⏳ Health check failed: {e.__class__.__name__}, retrying... ({elapsed}s elapsed)")

    raise Exception(f"Pod health check timed out after {timeout_seconds} seconds")


# Rest of the functions remain unchanged for brevity...
# [Including all other existing functions from the original file]

def get_pod_name(user_id: str, project_id: str):
    """
    Get the first running pod name for a project.
    """
    namespace = f"user-{user_id}"
    deployment_name = f"proj-{project_id}-api"

    try:
        # List pods with the deployment label
        pods = core_v1.list_namespaced_pod(
            namespace=namespace, label_selector=f"app={deployment_name}"
        )

        for pod in pods.items:
            if pod.status.phase == "Running":
                print(f"✓ Found running pod: {pod.metadata.name}")
                return pod.metadata.name

        raise Exception(f"No running pods found for deployment {deployment_name}")

    except ApiException as e:
        if e.status == 404:
            raise Exception(f"No pods found for deployment {deployment_name}")
        else:
            print(f"✗ Failed to list pods: {e}")
            raise e
    except Exception as e:
        print(f"✗ Unexpected error listing pods: {e}")
        raise e


def execute_git_clone(user_id: str, project_id: str, repo_url: str):
    """
    Execute git clone command on the running pod.
    """
    namespace = f"user-{user_id}"

    try:
        # Get the pod name
        pod_name = get_pod_name(user_id, project_id)

        print(f"🔧 Executing git clone on pod {pod_name}")
        print(f"📦 Repository: {repo_url}")

        # Build the clone command
        clone_script = f"""
set -e
echo "🔧 Starting repository clone..."
echo "📦 Repository URL: {repo_url}"
REPO_PATH=$(echo "{repo_url}" | sed 's|https://github.com/||' | sed 's|.git$||')
AUTHENTICATED_URL="https://${{GITHUB_PERSONAL_ACCESS_TOKEN}}@github.com/${{REPO_PATH}}.git"
echo "🌐 Formulated authenticated URL..."
git clone "$AUTHENTICATED_URL"
echo "🎉 Repository clone completed successfully!"
"""

        # Execute the command on the pod
        exec_command = ["/bin/sh", "-c", clone_script]

        resp = stream(
            core_v1.connect_get_namespaced_pod_exec,
            pod_name,
            namespace,
            command=exec_command,
            stderr=True,
            stdin=False,
            stdout=True,
            tty=False,
        )

        print(f"📄 Clone command output:")
        print(resp)

        # Check if the command succeeded (basic check)
        if "✅" in resp and "completed successfully" in resp:
            print(f"✅ Git clone executed successfully on pod {pod_name}")
            return True
        else:
            print(f"❌ Git clone may have failed. Output: {resp}")
            raise Exception(f"Git clone command failed: {resp}")

    except ApiException as e:
        print(f"✗ Failed to execute git clone: {e}")
        raise e
    except Exception as e:
        print(f"✗ Unexpected error during git clone: {e}")
        raise e


async def clone_repository_on_pod(
    user_id: str, project_id: str, repo_url: str, endpoint: str
):
    """
    Execute git clone command on pod.
    Assumes pod health has already been verified.
    """
    try:
        # Execute git clone command
        print(f"📂 Executing git clone command...")
        execute_git_clone(user_id, project_id, repo_url)

        print(f"🎉 Repository {repo_url} successfully cloned to project {project_id}")
        return True

    except Exception as e:
        print(f"❌ Failed to clone repository: {e}")
        raise e


def scale_project(user_id: str, project_id: str, replicas: int):
    """
    Scale a project's deployment to the specified number of replicas.
    """
    namespace = f"user-{user_id}"
    deployment_name = f"proj-{project_id}-api"

    try:
        # Use the scale subresource for atomic scaling
        scale_spec = client.V1Scale(
            metadata=client.V1ObjectMeta(name=deployment_name, namespace=namespace),
            spec=client.V1ScaleSpec(replicas=replicas),
        )

        apps_v1.patch_namespaced_deployment_scale(
            name=deployment_name, namespace=namespace, body=scale_spec
        )

        action = "activated" if replicas > 0 else "deactivated"
        print(
            f"✓ Successfully {action} project {project_id} (scaled to {replicas} replicas)"
        )

    except ApiException as e:
        if e.status == 404:
            raise Exception(
                f"Deployment {deployment_name} not found in namespace {namespace}"
            )
        else:
            print(f"✗ Failed to scale deployment {deployment_name}: {e}")
            raise e
    except Exception as e:
        print(f"✗ Unexpected error scaling deployment: {e}")
        raise e


def get_project_endpoint(user_id: str, project_id: str):
    """
    Get the LoadBalancer IP for a project service.
    This now assumes the endpoint exists (for use after creation).
    Returns None if not available instead of throwing exceptions.
    """
    if os.getenv("DEV_ENV") == "1":
        return "localhost:3001"

    namespace = f"user-{user_id}"
    service_name = f"proj-{project_id}-api"

    try:
        service = core_v1.read_namespaced_service(
            name=service_name, namespace=namespace
        )

        if (
            service.status
            and service.status.load_balancer
            and service.status.load_balancer.ingress
            and len(service.status.load_balancer.ingress) > 0
        ):

            ingress = service.status.load_balancer.ingress[0]
            if ingress.ip:
                print(f"✓ Found LoadBalancer IP: {ingress.ip}")
                return ingress.ip
            elif ingress.hostname:
                print(f"✓ Found LoadBalancer hostname: {ingress.hostname}")
                return ingress.hostname

        # For existing projects, return None instead of throwing
        return None

    except ApiException as e:
        if e.status == 404:
            return None
        else:
            print(f"✗ Failed to get service {service_name}: {e}")
            raise e
    except Exception as e:
        print(f"✗ Unexpected error getting LoadBalancer IP: {e}")
        raise e


def delete_project_resources(user_id: str, project_id: str):
    """
    Delete all Kubernetes resources for a project.
    """
    namespace = f"user-{user_id}"
    deployment_name = f"proj-{project_id}-api"
    service_name = f"proj-{project_id}-api"
    github_secret_name = f"proj-{project_id}-github-key"

    errors = []

    # Delete deployment
    try:
        apps_v1.delete_namespaced_deployment(
            name=deployment_name,
            namespace=namespace,
            body=client.V1DeleteOptions(
                propagation_policy="Foreground", grace_period_seconds=30
            ),
        )
        print(f"✓ Deleted deployment: {deployment_name}")
    except ApiException as e:
        if e.status == 404:
            print(f"ℹ Deployment {deployment_name} was already deleted")
        else:
            error_msg = f"Failed to delete deployment {deployment_name}: {e}"
            print(f"✗ {error_msg}")
            errors.append(error_msg)
    except Exception as e:
        error_msg = f"Unexpected error deleting deployment {deployment_name}: {e}"
        print(f"✗ {error_msg}")
        errors.append(error_msg)

    # Delete service
    try:
        core_v1.delete_namespaced_service(
            name=service_name,
            namespace=namespace,
            body=client.V1DeleteOptions(grace_period_seconds=10),
        )
        print(f"✓ Deleted service: {service_name}")
    except ApiException as e:
        if e.status == 404:
            print(f"ℹ Service {service_name} was already deleted")
        else:
            error_msg = f"Failed to delete service {service_name}: {e}"
            print(f"✗ {error_msg}")
            errors.append(error_msg)
    except Exception as e:
        error_msg = f"Unexpected error deleting service {service_name}: {e}"
        print(f"✗ {error_msg}")
        errors.append(error_msg)

    # Delete GitHub secret if it exists
    try:
        core_v1.delete_namespaced_secret(
            name=github_secret_name,
            namespace=namespace,
            body=client.V1DeleteOptions(grace_period_seconds=10),
        )
        print(f"✓ Deleted GitHub Secret: {github_secret_name}")
    except ApiException as e:
        if e.status == 404:
            print(f"ℹ GitHub Secret {github_secret_name} was already deleted")
        else:
            # Don't add to errors - secret might not exist
            print(f"⚠ Could not delete GitHub Secret {github_secret_name}: {e}")
    except Exception as e:
        print(f"⚠ Unexpected error deleting GitHub Secret {github_secret_name}: {e}")

    if errors:
        raise Exception(f"Some resources could not be deleted: {'; '.join(errors)}")


def update_github_secret(user_id: str, project_id: str, github_key: str = None):
    """
    Update or remove GitHub key secret for a project.
    """
    namespace = f"user-{user_id}"
    github_secret_name = f"proj-{project_id}-github-key"

    if github_key:
        # Create or update the secret
        try:
            # Check if secret already exists
            existing_secret = core_v1.read_namespaced_secret(
                name=github_secret_name, namespace=namespace
            )
            print(f"ℹ Updating existing GitHub Secret {github_secret_name}")

            # Update secret data
            secret_data = {
                "GITHUB_PERSONAL_ACCESS_TOKEN": base64.b64encode(
                    github_key.encode("utf-8")
                ).decode("utf-8")
            }
            existing_secret.data = secret_data

            core_v1.replace_namespaced_secret(
                name=github_secret_name, namespace=namespace, body=existing_secret
            )
            print(
                f"✓ Updated GitHub Secret {github_secret_name} in namespace {namespace}"
            )

        except ApiException as e:
            if e.status == 404:
                # Secret doesn't exist, create it
                secret_data = {
                    "GITHUB_PERSONAL_ACCESS_TOKEN": base64.b64encode(
                        github_key.encode("utf-8")
                    ).decode("utf-8")
                }
                secret_body = client.V1Secret(
                    metadata=client.V1ObjectMeta(
                        name=github_secret_name,
                        labels={
                            "managed-by": "k8s-manager",
                            "user-id": user_id,
                            "project-id": project_id,
                        },
                    ),
                    type="Opaque",
                    data=secret_data,
                )
                core_v1.create_namespaced_secret(namespace=namespace, body=secret_body)
                print(
                    f"✓ Created GitHub Secret {github_secret_name} in namespace {namespace}"
                )
            else:
                print(f"✗ Failed to update GitHub Secret: {e}")
                raise e
        except Exception as e:
            print(f"✗ Unexpected error updating GitHub Secret: {e}")
            raise e
    else:
        # Remove the secret
        try:
            core_v1.delete_namespaced_secret(
                name=github_secret_name,
                namespace=namespace,
                body=client.V1DeleteOptions(grace_period_seconds=10),
            )
            print(
                f"✓ Deleted GitHub Secret {github_secret_name} from namespace {namespace}"
            )
        except ApiException as e:
            if e.status == 404:
                print(f"ℹ GitHub Secret {github_secret_name} was already deleted")
            else:
                print(f"✗ Failed to delete GitHub Secret: {e}")
                raise e
        except Exception as e:
            print(f"✗ Unexpected error deleting GitHub Secret: {e}")
            raise e

    # If project is active, we need to restart the deployment to pick up new env vars
    deployment_name = f"proj-{project_id}-api"
    try:
        deployment = apps_v1.read_namespaced_deployment(
            name=deployment_name, namespace=namespace
        )
        if deployment.spec.replicas and deployment.spec.replicas > 0:
            # Restart deployment by updating annotation
            import time

            if not deployment.spec.template.metadata.annotations:
                deployment.spec.template.metadata.annotations = {}
            deployment.spec.template.metadata.annotations[
                "kubectl.kubernetes.io/restartedAt"
            ] = str(int(time.time()))

            apps_v1.patch_namespaced_deployment(
                name=deployment_name, namespace=namespace, body=deployment
            )
            print(
                f"✓ Restarted deployment {deployment_name} to pick up new GitHub token"
            )
    except ApiException as e:
        if e.status == 404:
            print(f"ℹ Deployment {deployment_name} not found, skipping restart")
        else:
            print(f"⚠ Warning: Could not restart deployment {deployment_name}: {e}")
    except Exception as e:
        print(f"⚠ Warning: Unexpected error restarting deployment: {e}")


# New function to create or update user-level GitHub secret
def create_or_update_user_github_secret(user_id: str, github_key: str):
    """
    Create or update a user-level GitHub secret for all projects.
    """
    namespace = f"user-{user_id}"
    github_secret_name = f"user-{user_id}-github-key"

    # Ensure namespace exists
    ensure_namespace(user_id)

    # Create or update the secret
    try:
        # Check if secret already exists
        try:
            existing_secret = core_v1.read_namespaced_secret(
                name=github_secret_name, namespace=namespace
            )
            print(f"ℹ Updating existing user GitHub Secret {github_secret_name}")

            # Update secret data
            secret_data = {
                "GITHUB_PERSONAL_ACCESS_TOKEN": base64.b64encode(
                    github_key.encode("utf-8")
                ).decode("utf-8")
            }
            existing_secret.data = secret_data

            core_v1.replace_namespaced_secret(
                name=github_secret_name, namespace=namespace, body=existing_secret
            )
            print(
                f"✓ Updated user GitHub Secret {github_secret_name} in namespace {namespace}"
            )

        except ApiException as e:
            if e.status == 404:
                # Secret doesn't exist, create it
                secret_data = {
                    "GITHUB_PERSONAL_ACCESS_TOKEN": base64.b64encode(
                        github_key.encode("utf-8")
                    ).decode("utf-8")
                }
                secret_body = client.V1Secret(
                    metadata=client.V1ObjectMeta(
                        name=github_secret_name,
                        labels={
                            "managed-by": "k8s-manager",
                            "user-id": user_id,
                            "type": "user-github-key",
                        },
                    ),
                    type="Opaque",
                    data=secret_data,
                )
                core_v1.create_namespaced_secret(namespace=namespace, body=secret_body)
                print(
                    f"✓ Created user GitHub Secret {github_secret_name} in namespace {namespace}"
                )
            else:
                print(f"✗ Failed to update user GitHub Secret: {e}")
                raise e
    except Exception as e:
        print(f"✗ Unexpected error with user GitHub Secret: {e}")
        raise e

    return github_secret_name


def delete_user_github_secret(user_id: str):
    """
    Delete the user-level GitHub secret.
    """
    namespace = f"user-{user_id}"
    github_secret_name = f"user-{user_id}-github-key"

    try:
        core_v1.delete_namespaced_secret(
            name=github_secret_name,
            namespace=namespace,
            body=client.V1DeleteOptions(grace_period_seconds=10),
        )
        print(
            f"✓ Deleted user GitHub Secret {github_secret_name} from namespace {namespace}"
        )
        return True
    except ApiException as e:
        if e.status == 404:
            print(
                f"ℹ User GitHub Secret {github_secret_name} was already deleted or doesn't exist"
            )
            return False
        else:
            print(f"✗ Failed to delete user GitHub Secret: {e}")
            raise e
    except Exception as e:
        print(f"✗ Unexpected error deleting user GitHub Secret: {e}")
        raise e


def get_user_github_secret(user_id: str):
    """
    Check if a user-level GitHub secret exists.
    """
    namespace = f"user-{user_id}"
    github_secret_name = f"user-{user_id}-github-key"

    try:
        secret = core_v1.read_namespaced_secret(
            name=github_secret_name, namespace=namespace
        )
        return True
    except ApiException as e:
        if e.status == 404:
            return False
        else:
            print(f"✗ Failed to check user GitHub Secret: {e}")
            raise e
    except Exception as e:
        print(f"✗ Unexpected error checking user GitHub Secret: {e}")
        raise e


def update_deployment_env_vars(user_id: str, project_id: str, env_vars: dict):
    """
    Update environment variables for a deployment and restart it.
    """
    namespace = f"user-{user_id}"
    deployment_name = f"proj-{project_id}-api"

    try:
        # Get current deployment
        deployment = apps_v1.read_namespaced_deployment(
            name=deployment_name, namespace=namespace
        )

        # Update environment variables in container spec
        container = deployment.spec.template.spec.containers[0]

        # Add new environment variables
        if not container.env:
            container.env = []

        # Remove existing env vars with same keys, then add new ones
        existing_env_names = {env.name for env in container.env}
        for key, value in env_vars.items():
            # Remove existing env var with same name
            container.env = [env for env in container.env if env.name != key]
            # Add new env var
            container.env.append(client.V1EnvVar(name=key, value=str(value)))

        # Force restart by updating restart annotation
        import time

        if not deployment.spec.template.metadata.annotations:
            deployment.spec.template.metadata.annotations = {}
        deployment.spec.template.metadata.annotations[
            "kubectl.kubernetes.io/restartedAt"
        ] = str(int(time.time()))

        # Apply the updated deployment
        apps_v1.patch_namespaced_deployment(
            name=deployment_name, namespace=namespace, body=deployment
        )

        print(
            f"✓ Updated environment variables and restarted deployment {deployment_name}"
        )
        print(f"  Added env vars: {list(env_vars.keys())}")

    except ApiException as e:
        if e.status == 404:
            raise Exception(
                f"Deployment {deployment_name} not found in namespace {namespace}"
            )
        else:
            print(f"✗ Failed to update deployment {deployment_name}: {e}")
            raise e
    except Exception as e:
        print(f"✗ Unexpected error updating deployment: {e}")
        raise e


def get_k8s_status():
    """
    Get the current status of Kubernetes connectivity.
    """
    config_source = "unknown"
    if KUBE_CONFIG_BASE64:
        config_source = "base64-encoded"
    elif KUBE_CONFIG:
        config_source = "custom-path"
    elif os.path.exists(os.path.expanduser("~/.kube/config")):
        config_source = "default-location"
    elif os.getenv("KUBERNETES_SERVICE_HOST"):
        config_source = "in-cluster"

    return {
        "available": k8s_available,
        "mode": "kubernetes",
        "config_source": config_source,
        "image": ACR_IMAGE,
    }
