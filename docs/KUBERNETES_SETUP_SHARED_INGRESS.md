# Kubernetes Setup – Shared Ingress with Static IP (Windows Command Prompt)

This guide provisions a shared ingress controller with a static public IP so every project uses ClusterIP Services and a single cloud load balancer. All commands use Windows `cmd.exe` syntax to match the existing workflow in `docs\KUBERNETES_SETUP.md`.

## Prerequisites
- Azure CLI (logged in with the subscription that owns your AKS cluster).
- `kubectl` configured to talk to the target cluster (`az aks get-credentials ...`).
- Administrator rights to create resources in the AKS node resource group.

## 1. Configure Environment Variables
Set the resource group that holds your AKS nodes (often ends with `-nodepool`), the region, and a DNS label for Azure’s managed hostname. If you do **not** want Azure to supply a hostname, run `set DNS_LABEL=` to clear it.

```
set RESOURCE_GROUP=<aks-node-resource-group>
set LOCATION=<azure-region>            REM example: eastus
set DNS_LABEL=goose-%RANDOM%            REM leave blank if you will bring your own DNS
set INGRESS_CLASS_NAME=nginx
```

## 2. Allocate a Standard Public IP (Optional Azure DNS Label)
The static IP backs the ingress controller. Azure only allocates the load balancer once, preventing per-pod provisioning delays.

```
if defined DNS_LABEL (
  az network public-ip create ^
    --resource-group %RESOURCE_GROUP% ^
    --name goose-static-ingress ^
    --sku Standard ^
    --allocation-method static ^
    --dns-name %DNS_LABEL% ^
    --location %LOCATION%
) else (
  az network public-ip create ^
    --resource-group %RESOURCE_GROUP% ^
    --name goose-static-ingress ^
    --sku Standard ^
    --allocation-method static ^
    --location %LOCATION%
)
```

Fetch the allocated IP and derive the public domain suffix the Python service expects. Keep the Azure `*.cloudapp.azure.com` name if you do not own a domain.

```
for /f "delims=" %I in ( ^
  'az network public-ip show --resource-group %RESOURCE_GROUP% --name goose-static-ingress --query "ipAddress" -o tsv' ^
) do set STATIC_INGRESS_IP=%I

if defined DNS_LABEL (
  set PUBLIC_APP_DOMAIN=%DNS_LABEL%.%LOCATION%.cloudapp.azure.com
) else (
  set PUBLIC_APP_DOMAIN=<your-domain.example.com>
)

echo Static ingress IP: %STATIC_INGRESS_IP%
echo Public app domain: %PUBLIC_APP_DOMAIN%
```

> **Important:** `PUBLIC_APP_DOMAIN` must be non-empty before launching `k8s_manager`. Using Azure’s generated value is sufficient even if end users never see the hostname.

## 3. Install the Shared Ingress Controller
Create the manifests using `echo` blocks (consistent with the existing setup docs) and apply them. This installs `ingress-nginx` with two replicas and binds the controller Service to the static IP.

```
if not exist infra mkdir infra

(
  echo apiVersion: v1
  echo kind: Namespace
  echo metadata:
  echo ^  name: ingress-nginx
  echo ^  labels:
  echo ^    app.kubernetes.io/name: ingress-nginx
  echo ---
  echo apiVersion: apps/v1
  echo kind: Deployment
  echo metadata:
  echo ^  name: ingress-nginx-controller
  echo ^  namespace: ingress-nginx
  echo spec:
  echo ^  replicas: 2
  echo ^  selector:
  echo ^    matchLabels:
  echo ^      app.kubernetes.io/name: ingress-nginx
  echo ^      app.kubernetes.io/component: controller
  echo ^  template:
  echo ^    metadata:
  echo ^      labels:
  echo ^        app.kubernetes.io/name: ingress-nginx
  echo ^        app.kubernetes.io/component: controller
  echo ^    spec:
  echo ^      serviceAccountName: ingress-nginx
  echo ^      containers:
  echo ^      - name: controller
  echo ^        image: registry.k8s.io/ingress-nginx/controller:v1.11.1
  echo ^        args:
  echo ^        - /nginx-ingress-controller
  echo ^        - --publish-service=$(POD_NAMESPACE)/ingress-nginx-controller
  echo ^        - --ingress-class=%INGRESS_CLASS_NAME%
  echo ^        readinessProbe:
  echo ^          httpGet:
  echo ^            path: /healthz
  echo ^            port: 10254
  echo ^        livenessProbe:
  echo ^          httpGet:
  echo ^            path: /healthz
  echo ^            port: 10254
  echo ---
  echo apiVersion: v1
  echo kind: Service
  echo metadata:
  echo ^  name: ingress-nginx-controller
  echo ^  namespace: ingress-nginx
  echo ^  annotations:
  echo ^    service.beta.kubernetes.io/azure-load-balancer-health-probe-request-path: /healthz
  echo spec:
  echo ^  type: LoadBalancer
  echo ^  loadBalancerIP: %STATIC_INGRESS_IP%
  echo ^  externalTrafficPolicy: Local
  echo ^  ports:
  echo ^  - name: http
  echo ^    port: 80
  echo ^    targetPort: 80
  echo ^  - name: https
  echo ^    port: 443
  echo ^    targetPort: 443
  echo ^  selector:
  echo ^    app.kubernetes.io/name: ingress-nginx
  echo ^    app.kubernetes.io/component: controller
) > infra\ingress-nginx.yaml

kubectl apply -f infra\ingress-nginx.yaml
```

Confirm Kubernetes attached the controller to the static IP.

```
kubectl get service ingress-nginx-controller -n ingress-nginx -o jsonpath="{.status.loadBalancer.ingress[0].ip}\n"
```

## 4. Prepare Per-User Namespaces (Quota, Security, RBAC)
These steps mirror `docs\KUBERNETES_SETUP.md` but tailored for the shared ingress. Replace `<user-id>` with the actual identifier.

```
set USER_ID=<user>
set PROJECT_ID=<project>
set NAMESPACE=user-%USER_ID%

kubectl create namespace %NAMESPACE%

(
  echo apiVersion: v1
  echo kind: ResourceQuota
  echo metadata:
  echo ^  name: %NAMESPACE%-quota
  echo ^  namespace: %NAMESPACE%
  echo spec:
  echo ^  hard:
  echo ^    requests.cpu: "2"
  echo ^    requests.memory: 4Gi
  echo ^    limits.cpu: "4"
  echo ^    limits.memory: 8Gi
  echo ^    persistentvolumeclaims: "2"
) > quota.yaml

kubectl apply -f quota.yaml

type quota.yaml
```

Label the namespace for Pod Security and optional NetworkPolicy as needed.

```
kubectl label namespace %NAMESPACE% pod-security.kubernetes.io/enforce=restricted --overwrite
```

## 5. Create Project Service/Ingress Manifests
Each project now uses a ClusterIP Service and an Ingress that reuses the shared controller. The hostname follows `<project-id>-<user-id>.%PUBLIC_APP_DOMAIN%` to align with `k8s_manager` logic.

```
set PROJECT_HOST=%PROJECT_ID%-%USER_ID%.%PUBLIC_APP_DOMAIN%

if not exist environments mkdir environments
if not exist environments\%NAMESPACE% mkdir environments\%NAMESPACE%
if not exist environments\%NAMESPACE%\proj-%PROJECT_ID% mkdir environments\%NAMESPACE%\proj-%PROJECT_ID%

(
  echo apiVersion: v1
  echo kind: Service
  echo metadata:
  echo ^  name: proj-%PROJECT_ID%-api
  echo ^  namespace: %NAMESPACE%
  echo ^  labels:
  echo ^    app: proj-%PROJECT_ID%-api
  echo ^    project-id: %PROJECT_ID%
  echo ^    user-id: %USER_ID%
  echo spec:
  echo ^  selector:
  echo ^    app: proj-%PROJECT_ID%-api
  echo ^  ports:
  echo ^  - name: http
  echo ^    port: 80
  echo ^    targetPort: 3001
  echo ^  type: ClusterIP
) > environments\%NAMESPACE%\proj-%PROJECT_ID%\service.yaml

(
  echo apiVersion: networking.k8s.io/v1
  echo kind: Ingress
  echo metadata:
  echo ^  name: proj-%PROJECT_ID%-api
  echo ^  namespace: %NAMESPACE%
  echo ^  annotations:
  echo ^    kubernetes.io/ingress.class: %INGRESS_CLASS_NAME%
  echo spec:
  echo ^  rules:
  echo ^  - host: %PROJECT_HOST%
  echo ^    http:
  echo ^      paths:
  echo ^      - path: /
  echo ^        pathType: Prefix
  echo ^        backend:
  echo ^          service:
  echo ^            name: proj-%PROJECT_ID%-api
  echo ^            port:
  echo ^              number: 80
) > environments\%NAMESPACE%\proj-%PROJECT_ID%\ingress.yaml

REM Append TLS configuration manually if cert-manager or another issuer provisions certificates for %PROJECT_HOST%

kubectl apply -f environments\%NAMESPACE%\proj-%PROJECT_ID%\service.yaml
kubectl apply -f environments\%NAMESPACE%\proj-%PROJECT_ID%\ingress.yaml
```

## 6. Deploy the Application
At this point only Deployment and ConfigMap/Secret resources are missing. You can reuse the deployment template from `docs\KUBERNETES_SETUP.md` but keep its Service definition removed (the shared ingress already covers external access).

```
(
  echo apiVersion: apps/v1
  echo kind: Deployment
  echo metadata:
  echo ^  name: proj-%PROJECT_ID%-api
  echo ^  namespace: %NAMESPACE%
  echo spec:
  echo ^  replicas: 1
  echo ^  selector:
  echo ^    matchLabels:
  echo ^      app: proj-%PROJECT_ID%-api
  echo ^  template:
  echo ^    metadata:
  echo ^      labels:
  echo ^        app: proj-%PROJECT_ID%-api
  echo ^        project-id: %PROJECT_ID%
  echo ^        user-id: %USER_ID%
  echo ^    spec:
  echo ^      containers:
  echo ^      - name: api
  echo ^        image: <acr>.azurecr.io/goose-api-server:latest
  echo ^        ports:
  echo ^        - containerPort: 3001
  echo ^        readinessProbe:
  echo ^          httpGet:
  echo ^            path: /api/v1/health
  echo ^            port: 3001
  echo ^        livenessProbe:
  echo ^          httpGet:
  echo ^            path: /api/v1/health
  echo ^            port: 3001
  echo ^        resources:
  echo ^          requests:
  echo ^            cpu: "500m"
  echo ^            memory: "1Gi"
  echo ^          limits:
  echo ^            cpu: "1000m"
  echo ^            memory: "2Gi"
) > environments\%NAMESPACE%\proj-%PROJECT_ID%\deployment.yaml

kubectl apply -f environments\%NAMESPACE%\proj-%PROJECT_ID%\deployment.yaml
```

## 7. Configure `k8s_manager`
The Python service expects the following environment variables before startup (set them wherever the app runs):

```
set PUBLIC_APP_DOMAIN=%PUBLIC_APP_DOMAIN%
set INGRESS_CLASS_NAME=%INGRESS_CLASS_NAME%
REM Optional if you use TLS secrets patterned by project/user
set INGRESS_TLS_SECRET_PATTERN=proj-{project_id}-tls
```

Confirm that new projects now report the ingress hostname immediately:

```
python -c "from k8s_manager.services import k8s_service; print(k8s_service.build_project_host('%USER_ID%', '%PROJECT_ID%'))"
```

## 8. Verification
1. `kubectl get svc -A | find "ingress-nginx-controller"` — should show the static `EXTERNAL-IP`.
2. `kubectl get ingress -n %NAMESPACE%` — confirm hosts match `<project>-<user>.%PUBLIC_APP_DOMAIN%`.
3. `curl http://%PROJECT_HOST%/api/v1/health` — succeeds once the deployment is ready (add `--resolve` with the static IP if testing before DNS propagates).

With the shared ingress in place, pod activations no longer wait for per-project load balancer provisioning. Azure keeps the single load balancer alive, and Kubernetes only needs to register backend endpoints, stabilizing startup time.
