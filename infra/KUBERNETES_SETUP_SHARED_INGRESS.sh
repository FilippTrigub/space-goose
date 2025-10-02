#!/usr/bin/env bash
set -euo pipefail

# Kubernetes Cluster Setup with Shared Ingress & Static Public IP (Linux)
# Mirrors docs/KUBERNETES_SETUP.md but provisions a single ingress-nginx controller
# so individual projects only need ClusterIP Services.

# =============================
# 0. Prerequisites
# =============================
# - Azure CLI authenticated (az login) and correct subscription selected
# - kubectl context set to the target AKS cluster (az aks get-credentials ...)
# - Bash shell (Ubuntu or similar)

# =============================
# 1. Global Settings (edit as needed)
# =============================
AKS_RESOURCE_GROUP="goose-aks"
AKS_CLUSTER_NAME="goose-flock"
AKS_LOCATION="francecentral"        # e.g. eastus
AKS_NODE_VM_SIZE="Standard_D4s_v3"
AKS_NODE_COUNT=3
CREATE_AKS_CLUSTER=true               # set to false if cluster already exists

DNS_LABEL="goose-$RANDOM"            # set to empty string if you will supply your own DNS later
INGRESS_CLASS_NAME="nginx"
ACR_IMAGE="caf0957b5c26acr.azurecr.io/goose-api-server:3009251931"
USER_ID="main"
PROJECT_ID="goose-api-main"
NAMESPACE="user-${USER_ID}"

# =============================
# 1a. (Optional) Create AKS Cluster
# =============================
if [[ "$CREATE_AKS_CLUSTER" == "true" ]]; then
  az group create \
    --name "$AKS_RESOURCE_GROUP" \
    --location "$AKS_LOCATION"

  az aks create \
    --resource-group "$AKS_RESOURCE_GROUP" \
    --name "$AKS_CLUSTER_NAME" \
    --location "$AKS_LOCATION" \
    --vm-set-type VirtualMachineScaleSets \
    --node-count "$AKS_NODE_COUNT" \
    --node-vm-size "$AKS_NODE_VM_SIZE" \
    --generate-ssh-keys
fi

az aks get-credentials \
  --resource-group "$AKS_RESOURCE_GROUP" \
  --name "$AKS_CLUSTER_NAME" \
  --overwrite-existing

NODE_RESOURCE_GROUP=$(az aks show \
  --resource-group "$AKS_RESOURCE_GROUP" \
  --name "$AKS_CLUSTER_NAME" \
  --query "nodeResourceGroup" -o tsv)

RESOURCE_GROUP="$NODE_RESOURCE_GROUP"
LOCATION="$AKS_LOCATION"

# =============================
# 2. Allocate Static Public IP (optional Azure DNS label)
# =============================
if [[ -n "$DNS_LABEL" ]]; then
  az network public-ip create \
    --resource-group "$RESOURCE_GROUP" \
    --name goose-static-ingress \
    --sku Standard \
    --allocation-method static \
    --dns-name "$DNS_LABEL" \
    --location "$LOCATION"
else
  az network public-ip create \
    --resource-group "$RESOURCE_GROUP" \
    --name goose-static-ingress \
    --sku Standard \
    --allocation-method static \
    --location "$LOCATION"
fi

STATIC_INGRESS_IP=$(az network public-ip show \
  --resource-group "$RESOURCE_GROUP" \
  --name goose-static-ingress \
  --query "ipAddress" -o tsv)

if [[ -n "$DNS_LABEL" ]]; then
  PUBLIC_APP_DOMAIN="${DNS_LABEL}.${LOCATION}.cloudapp.azure.com"
else
  PUBLIC_APP_DOMAIN="<your-domain.example.com>"
fi

export STATIC_INGRESS_IP PUBLIC_APP_DOMAIN INGRESS_CLASS_NAME USER_ID PROJECT_ID NAMESPACE

echo "Static ingress IP: $STATIC_INGRESS_IP"
echo "Public app domain: $PUBLIC_APP_DOMAIN"

# =============================
# 3. Install ingress-nginx Controller
# =============================
mkdir -p infra
cat <<EOF > infra/ingress-nginx.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: ingress-nginx
  labels:
    app.kubernetes.io/name: ingress-nginx
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ingress-nginx-controller
  namespace: ingress-nginx
spec:
  replicas: 2
  selector:
    matchLabels:
      app.kubernetes.io/name: ingress-nginx
      app.kubernetes.io/component: controller
  template:
    metadata:
      labels:
        app.kubernetes.io/name: ingress-nginx
        app.kubernetes.io/component: controller
    spec:
      serviceAccountName: ingress-nginx
      containers:
        - name: controller
          image: registry.k8s.io/ingress-nginx/controller:v1.11.1
          args:
            - /nginx-ingress-controller
            - --publish-service=\$(POD_NAMESPACE)/ingress-nginx-controller
            - --ingress-class=\${INGRESS_CLASS_NAME}
          readinessProbe:
            httpGet:
              path: /healthz
              port: 10254
          livenessProbe:
            httpGet:
              path: /healthz
              port: 10254
---
apiVersion: v1
kind: Service
metadata:
  name: ingress-nginx-controller
  namespace: ingress-nginx
  annotations:
    service.beta.kubernetes.io/azure-load-balancer-health-probe-request-path: /healthz
spec:
  type: LoadBalancer
  loadBalancerIP: ${STATIC_INGRESS_IP}
  externalTrafficPolicy: Local
  ports:
    - name: http
      port: 80
      targetPort: 80
    - name: https
      port: 443
      targetPort: 443
  selector:
    app.kubernetes.io/name: ingress-nginx
    app.kubernetes.io/component: controller
EOF

kubectl apply -f infra/ingress-nginx.yaml
kubectl get service ingress-nginx-controller -n ingress-nginx -o wide

# =============================
# 4. Namespace, Quota, Security
# =============================
kubectl create namespace "$NAMESPACE"

cat <<EOF > quota.yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: ${NAMESPACE}-quota
  namespace: ${NAMESPACE}
spec:
  hard:
    requests.cpu: "1"
    requests.memory: 2Gi
    limits.cpu: "2"
    limits.memory: 4Gi
    persistentvolumeclaims: "2"
EOF

kubectl apply -f quota.yaml
kubectl label namespace "$NAMESPACE" pod-security.kubernetes.io/enforce=restricted --overwrite

cat <<EOF > ${NAMESPACE}-networkpolicy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-platform-gateway
  namespace: ${NAMESPACE}
spec:
  podSelector:
    matchLabels:
      app: proj-${PROJECT_ID}-api
  policyTypes:
    - Ingress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              role: platform-gateway
      ports:
        - protocol: TCP
          port: 3001
EOF

kubectl apply -f ${NAMESPACE}-networkpolicy.yaml

# =============================
# 5. Service Account, RBAC, ConfigMap
# =============================
kubectl create serviceaccount ${PROJECT_ID}-bot -n ${NAMESPACE}

kubectl create role ${PROJECT_ID}-ops -n ${NAMESPACE} \
  --verb=get,list,watch,create,update,delete \
  --resource=deployments,statefulsets,services,ingresses,configmaps,secrets,pods

kubectl create rolebinding ${PROJECT_ID}-ops-binding -n ${NAMESPACE} \
  --role=${PROJECT_ID}-ops \
  --serviceaccount=${NAMESPACE}:${PROJECT_ID}-bot

kubectl create configmap ${PROJECT_ID}-env --from-env-file=.env -n ${NAMESPACE}

# =============================
# 6. Deployment
# =============================
cat <<EOF > deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: proj-${PROJECT_ID}-api
  namespace: ${NAMESPACE}
spec:
  replicas: 1
  selector:
    matchLabels:
      app: proj-${PROJECT_ID}-api
  template:
    metadata:
      labels:
        app: proj-${PROJECT_ID}-api
        project-id: ${PROJECT_ID}
        user-id: ${USER_ID}
    spec:
      serviceAccountName: ${PROJECT_ID}-bot
      containers:
        - name: api
          image: ${ACR_IMAGE}
          envFrom:
            - configMapRef:
                name: ${PROJECT_ID}-env
          ports:
            - containerPort: 3001
          readinessProbe:
            httpGet:
              path: /api/v1/health
              port: 3001
            initialDelaySeconds: 10
          livenessProbe:
            httpGet:
              path: /api/v1/health
              port: 3001
            initialDelaySeconds: 30
          resources:
            requests:
              cpu: "500m"
              memory: "1Gi"
            limits:
              cpu: "1000m"
              memory: "2Gi"
EOF

kubectl apply -f deployment.yaml

# =============================
# 7. ClusterIP Service & Ingress
# =============================
mkdir -p environments/${NAMESPACE}/proj-${PROJECT_ID}
PROJECT_HOST="${PROJECT_ID}-${USER_ID}.${PUBLIC_APP_DOMAIN}"

cat <<EOF > environments/${NAMESPACE}/proj-${PROJECT_ID}/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: proj-${PROJECT_ID}-api
  namespace: ${NAMESPACE}
  labels:
    app: proj-${PROJECT_ID}-api
    project-id: ${PROJECT_ID}
    user-id: ${USER_ID}
spec:
  selector:
    app: proj-${PROJECT_ID}-api
  ports:
    - name: http
      port: 80
      targetPort: 3001
  type: ClusterIP
EOF

kubectl apply -f environments/${NAMESPACE}/proj-${PROJECT_ID}/service.yaml

cat <<EOF > environments/${NAMESPACE}/proj-${PROJECT_ID}/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: proj-${PROJECT_ID}-api
  namespace: ${NAMESPACE}
  annotations:
    kubernetes.io/ingress.class: ${INGRESS_CLASS_NAME}
spec:
  rules:
    - host: ${PROJECT_HOST}
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: proj-${PROJECT_ID}-api
                port:
                  number: 80
EOF

kubectl apply -f environments/${NAMESPACE}/proj-${PROJECT_ID}/ingress.yaml

# =============================
# 8. Verification
# =============================
kubectl get svc ingress-nginx-controller -n ingress-nginx
kubectl get ingress -n ${NAMESPACE}

echo "Shared ingress setup complete."
echo "Export these variables for k8s_manager runtime:"
echo "  export PUBLIC_APP_DOMAIN=${PUBLIC_APP_DOMAIN}"
echo "  export INGRESS_CLASS_NAME=${INGRESS_CLASS_NAME}"
echo "  # export INGRESS_TLS_SECRET_PATTERN=proj-{project_id}-tls (optional if automating TLS)"
