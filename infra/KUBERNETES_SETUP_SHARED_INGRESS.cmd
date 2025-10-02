@echo off
REM Kubernetes Cluster Setup with Shared Ingress & Static Public IP
REM Mirrors docs/KUBERNETES_SETUP.md but replaces per-project LoadBalancer Services
REM with a single ingress controller fronting ClusterIP Services.

REM =============================
REM 0. Prerequisites
REM =============================
REM - Azure CLI logged in (az login) and correct subscription selected.
REM - `kubectl` connected to the target AKS cluster.
REM - Running in Windows Command Prompt (cmd.exe).

REM =============================
REM 1. Global Settings
REM =============================
set AKS_RESOURCE_GROUP=<aks-resource-group>
set AKS_CLUSTER_NAME=<aks-cluster-name>
set AKS_LOCATION=<azure-region>         REM example: eastus
set AKS_NODE_VM_SIZE=Standard_D4s_v3
set AKS_NODE_COUNT=3
set CREATE_AKS_CLUSTER=YES              REM set to NO if cluster already exists
set DNS_LABEL=goose-%RANDOM%            REM set blank ("set DNS_LABEL=") to skip Azure DNS label
set INGRESS_CLASS_NAME=nginx
set ACR_IMAGE=caf0957b5c26acr.azurecr.io/goose-api-server:2609251236

REM =============================
REM 1b. (Optional) Create AKS Cluster
REM =============================
if /I "%CREATE_AKS_CLUSTER%"=="YES" (
  az group create ^
    --name %AKS_RESOURCE_GROUP% ^
    --location %AKS_LOCATION%

  az aks create ^
    --resource-group %AKS_RESOURCE_GROUP% ^
    --name %AKS_CLUSTER_NAME% ^
    --location %AKS_LOCATION% ^
    --vm-set-type VirtualMachineScaleSets ^
    --node-count %AKS_NODE_COUNT% ^
    --node-vm-size %AKS_NODE_VM_SIZE% ^
    --generate-ssh-keys
)

az aks get-credentials ^
  --resource-group %AKS_RESOURCE_GROUP% ^
  --name %AKS_CLUSTER_NAME% ^
  --overwrite-existing

for /f "delims=" %%I in ( ^
  'az aks show --resource-group %AKS_RESOURCE_GROUP% --name %AKS_CLUSTER_NAME% --query "nodeResourceGroup" -o tsv' ^
) do set RESOURCE_GROUP=%%I

set LOCATION=%AKS_LOCATION%

REM =============================
REM 2. Static Public IP (Shared Ingress Front Door)
REM =============================
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

for /f "delims=" %%I in ( ^
  'az network public-ip show --resource-group %RESOURCE_GROUP% --name goose-static-ingress --query "ipAddress" -o tsv' ^
) do set STATIC_INGRESS_IP=%%I

if defined DNS_LABEL (
  set PUBLIC_APP_DOMAIN=%DNS_LABEL%.%LOCATION%.cloudapp.azure.com
) else (
  set PUBLIC_APP_DOMAIN=<your-domain.example.com>
)

echo Static ingress IP: %STATIC_INGRESS_IP%
echo Public app domain: %PUBLIC_APP_DOMAIN%

REM =============================
REM 3. Install Shared ingress-nginx Controller
REM =============================
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
echo ^        - --publish-service=^$(POD_NAMESPACE^)/ingress-nginx-controller
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

kubectl get service ingress-nginx-controller -n ingress-nginx -o wide

REM =============================
REM 4. Create User Namespace & Guardrails (Example user/project)
REM =============================
set USER_ID=goose-user1
set PROJECT_ID=goose-api-main
set NAMESPACE=user-%USER_ID%
set PROJECT_HOST=%PROJECT_ID%-%USER_ID%.%PUBLIC_APP_DOMAIN%

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

kubectl label namespace %NAMESPACE% pod-security.kubernetes.io/enforce=restricted --overwrite

REM optional network policy example
(
  echo apiVersion: networking.k8s.io/v1
  echo kind: NetworkPolicy
  echo metadata:
  echo ^  name: allow-platform-gateway
  echo ^  namespace: %NAMESPACE%
  echo spec:
  echo ^  podSelector:
  echo ^    matchLabels:
  echo ^      app: proj-%PROJECT_ID%-api
  echo ^  policyTypes:
  echo ^  - Ingress
  echo ^  ingress:
  echo ^  - from:
  echo ^    - namespaceSelector:
  echo ^        matchLabels:
  echo ^          role: platform-gateway
  echo ^    ports:
  echo ^    - protocol: TCP
  echo ^      port: 3001
) > %NAMESPACE%-networkpolicy.yaml

kubectl apply -f %NAMESPACE%-networkpolicy.yaml

type %NAMESPACE%-networkpolicy.yaml

REM =============================
REM 5. ConfigMap, ServiceAccount, RBAC (optional but recommended)
REM =============================
kubectl create serviceaccount %PROJECT_ID%-bot -n %NAMESPACE%

kubectl create role %PROJECT_ID%-ops -n %NAMESPACE% --verb=get,list,watch,create,update,delete --resource=deployments,statefulsets,services,ingresses,configmaps,secrets,pods

kubectl create rolebinding %PROJECT_ID%-ops-binding -n %NAMESPACE% --role=%PROJECT_ID%-ops --serviceaccount=%NAMESPACE%:%PROJECT_ID%-bot

REM Example configmap from .env
kubectl create configmap %PROJECT_ID%-env --from-env-file=.env -n %NAMESPACE%

REM =============================
REM 6. Deployment (Container workload)
REM =============================
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
  echo ^      serviceAccountName: %PROJECT_ID%-bot
  echo ^      containers:
  echo ^      - name: api
  echo ^        image: %ACR_IMAGE%
  echo ^        envFrom:
  echo ^        - configMapRef:
  echo ^            name: %PROJECT_ID%-env
  echo ^        ports:
  echo ^        - containerPort: 3001
  echo ^        readinessProbe:
  echo ^          httpGet:
  echo ^            path: /api/v1/health
  echo ^            port: 3001
  echo ^          initialDelaySeconds: 10
  echo ^        livenessProbe:
  echo ^          httpGet:
  echo ^            path: /api/v1/health
  echo ^            port: 3001
  echo ^          initialDelaySeconds: 30
  echo ^        resources:
  echo ^          requests:
  echo ^            cpu: "500m"
  echo ^            memory: "1Gi"
  echo ^          limits:
  echo ^            cpu: "1000m"
  echo ^            memory: "2Gi"
) > deployment.yaml

kubectl apply -f deployment.yaml

type deployment.yaml

REM =============================
REM 7. ClusterIP Service & Ingress (Shared Load Balancer)
REM =============================
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

kubectl apply -f environments\%NAMESPACE%\proj-%PROJECT_ID%\service.yaml

type environments\%NAMESPACE%\proj-%PROJECT_ID%\service.yaml

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

kubectl apply -f environments\%NAMESPACE%\proj-%PROJECT_ID%\ingress.yaml

type environments\%NAMESPACE%\proj-%PROJECT_ID%\ingress.yaml

REM =============================
REM 8. Verification & Runtime Operations
REM =============================
REM Fetch ingress hostname and static IP mapping
kubectl get ingress -n %NAMESPACE%

REM Optional: curl the health endpoint (requires DNS or hosts entry for %PROJECT_HOST%)
REM curl http://%PROJECT_HOST%/api/v1/health

REM Scale down/up as needed
kubectl scale deployment proj-%PROJECT_ID%-api -n %NAMESPACE% --replicas=0
kubectl scale deployment proj-%PROJECT_ID%-api -n %NAMESPACE% --replicas=1

REM =============================
REM 9. Environment Variables for k8s_manager
REM =============================
REM Ensure these are set wherever the Python service runs
set PUBLIC_APP_DOMAIN=%PUBLIC_APP_DOMAIN%
set INGRESS_CLASS_NAME=%INGRESS_CLASS_NAME%
REM set INGRESS_TLS_SECRET_PATTERN=proj-{project_id}-tls    REM optional TLS automation

@echo on
