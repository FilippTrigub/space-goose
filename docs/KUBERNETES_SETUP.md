# Kubernetes-Based Isolated Environment Research

## Executive Summary
- Namespaces, resource quotas, Pod Security admission, and network policies let us segment an AKS (or generic Kubernetes) cluster so each user project operates in an isolated slice with constrained compute/storage. https://kubernetes.io/docs/concepts/cluster-administration/multi-tenancy/ https://kubernetes.io/docs/concepts/policy/resource-quotas/ https://kubernetes.io/docs/concepts/security/pod-security-admission/ https://kubernetes.io/docs/concepts/services-networking/network-policies/
- Per-user service accounts and RBAC bindings allow the platform to enforce that each user can only manage their project namespaces, while Azure AD workload identity integrates cluster access with existing identities. https://kubernetes.io/docs/reference/access-authn-authz/rbac/ https://kubernetes.io/docs/tasks/configure-pod-container/configure-service-account/ https://learn.microsoft.com/en-us/azure/aks/workload-identity-overview
- Deployments (or StatefulSets) per project handle container lifecycle; scaling replicas between 0 and 1 activates/deactivates an environment on demand, and autoscalers like KEDA or Knative can automate scale-to-zero on inactivity. https://kubernetes.io/docs/concepts/workloads/controllers/deployment/#scaling-a-deployment https://keda.sh/docs/2.14/concepts/scaling-deployments/ https://knative.dev/docs/serving/autoscaling/autoscaler-types/#scale-to-zero
- Services and Ingress objects expose per-environment endpoints; retrieving ingress hostnames or service load balancer IPs gives the FQDN we need to hand back to the user app. https://kubernetes.io/docs/tasks/access-application-cluster/access-cluster-services/ https://kubernetes.io/docs/concepts/services-networking/ingress/ https://kubernetes.io/docs/reference/kubectl/jsonpath/

## Research Iterations
### Iteration 1 – Multi-tenant Isolation Building Blocks
- Kubernetes recommends namespaces as the primary tenancy boundary; we can create one namespace per user project and attach resource quotas and limits. https://kubernetes.io/docs/concepts/cluster-administration/multi-tenancy/
- Creating namespaces via `kubectl create namespace` (or REST) is straightforward and scriptable. https://kubernetes.io/docs/tasks/administer-cluster/namespaces/#creating-a-new-namespace
- ResourceQuota and LimitRange guardrails keep runaway usage in check per environment. https://kubernetes.io/docs/concepts/policy/resource-quotas/

### Iteration 2 – Security Controls & Identity
- Pod Security Admission enforces baseline, restricted, or privileged settings per namespace—critical when running arbitrary user workloads. https://kubernetes.io/docs/concepts/security/pod-security-admission/
- NetworkPolicy isolates traffic so containers only accept requests from the user’s gateway or API tier, preventing cross-tenant access. https://kubernetes.io/docs/concepts/services-networking/network-policies/
- RBAC Roles and RoleBindings scoped to namespaces ensure only the owning service account (or Azure AD workload identity) can manipulate project resources. https://kubernetes.io/docs/reference/access-authn-authz/rbac/ https://learn.microsoft.com/en-us/azure/aks/workload-identity-overview

### Iteration 3 – Lifecycle Management & Activation
- Deployments describe the container image, environment variables, secrets, and volumes; scaling replicas to 1 starts the environment, and 0 tears it down without deleting configuration. https://kubernetes.io/docs/concepts/workloads/controllers/deployment/#scaling-a-deployment
- KEDA provides event-driven autoscaling (including scale-to-zero) driven by metrics like HTTP activity or queue depth—useful for automatically suspending idle environments. https://keda.sh/docs/2.14/concepts/scaling-deployments/
- Knative Serving’s autoscaler can also scale pods to zero on no traffic; if we adopt it, ensure it integrates cleanly with namespace per tenant. https://knative.dev/docs/serving/autoscaling/autoscaler-types/#scale-to-zero

### Iteration 4 – Exposure & Observability
- Services (ClusterIP, LoadBalancer) and Ingress routes map user-facing hostnames to per-project deployments. https://kubernetes.io/docs/concepts/services-networking/ingress/
- `kubectl get service` and JSONPath queries pull the external IP/hostname required to communicate with the environment; similar commands target Ingress hostnames. https://kubernetes.io/docs/tasks/access-application-cluster/access-cluster-services/ https://kubernetes.io/docs/reference/kubectl/jsonpath/
- AKS operator best practices highlight extra hardening (dedicated node pools, network policy enforcement, Azure Policy) we should incorporate. https://learn.microsoft.com/en-us/azure/aks/operator-best-practices-cluster-isolation

### Iteration 5 – Advanced Isolation Options
- Virtual clusters (vCluster) or capsule-based multi-tenancy add stronger isolation by provisioning a lightweight control plane per tenant at the cost of extra complexity. https://www.vcluster.com/docs/architecture/what-is-a-virtual-cluster
- AKS Pod Sandboxing (Kata Confidential Containers) introduces hardware-backed isolation for untrusted workloads; evaluate if we need it for AI agent code execution. https://learn.microsoft.com/en-us/azure/aks/use-pod-sandboxing

## Proposed Architecture
1. **Namespace per project** with ResourceQuota, LimitRange, Pod Security labels, and NetworkPolicies that only allow traffic from the platform ingress/controller.
2. **Service account & RBAC**: create a service account tied to the user app; bind Roles for Deployment, Service, ConfigMap, Secret management inside that namespace only.
3. **Deployment/StatefulSet per environment** specifying the container image, env vars, mounted persistent volumes, and secrets (from Azure Key Vault CSI driver if needed).
4. **Service + Ingress/HTTPRoute** objects for API exposure; assign per-user hostnames (e.g., `<project>.env.example.com`) and TLS certificates.
5. **Activation/Deactivation**: platform backend hits the Kubernetes API to scale deployments to 1 on access, and either scales to 0 on exit or lets KEDA/Knative enforce idle scale-down.
6. **Automation**: use Infrastructure as Code (Helm, Kustomize, or Flux/GitOps) or a custom operator to reconcile desired state with actual cluster resources.
7. **Observability**: send namespace-scoped logs/metrics to Azure Monitor or Prometheus/Grafana with per-tenant filters.

## Command Recipes
```sh
# 1. Create namespace for the user project
kubectl create namespace testuser

# 2. Apply resource quota and limits
(
echo apiVersion: v1
echo kind: ResourceQuota
echo metadata:
echo ^  name: testuser-quota
echo ^  namespace: testuser
echo spec:
echo ^  hard:
echo ^    requests.cpu: '2'
echo ^    requests.memory: 4Gi
echo ^    limits.cpu: '4'
echo ^    limits.memory: 8Gi
echo ^    persistentvolumeclaims: '2'
) > quota.yaml

kubectl apply -f quota.yaml


# 3. Enforce Pod Security baseline + NetworkPolicy
kubectl label namespace testuser pod-security.kubernetes.io/enforce=restricted
(
echo apiVersion: networking.k8s.io/v1
echo kind: NetworkPolicy
echo metadata:
echo ^  name: allow-platform-gateway
echo ^  namespace: testuser
echo spec:
echo ^  podSelector:
echo ^    matchLabels:
echo ^      app: testuser-api
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
) > testuser-networkpolicy.yaml

kubectl apply -f testuser-networkpolicy.yaml

# 4. Create service account and RBAC binding
kubectl create serviceaccount testuser-bot -n testuser
kubectl create role testuser-ops -n testuser --verb=get,list,watch,create,update,delete --resource=deployments,statefulsets,services,ingresses,configmaps,secrets,pods
kubectl create rolebinding testuser-ops-binding -n testuser --role=testuser-ops --serviceaccount=testuser:testuser-bot

# 4b. Load environment variables from a .env file (use a Secret instead of ConfigMap for sensitive values)
kubectl create configmap testuser-env --from-env-file=.env -n testuser

# 5. Deploy the container image with environment variables
#    (restricted PodSecurity profile requires non-root run, dropped capabilities,
#     seccomp RuntimeDefault, allowPrivilegeEscalation=false, and explicit runAsUser/runAsGroup when
#     the container image defines a non-numeric user (e.g., USER goose).
#    ResourceQuota enforcement also means each container must set requests/limits for CPU and memory.

(
echo apiVersion: apps/v1
echo kind: Deployment
echo metadata:
echo ^  name: testuser-api
echo ^  namespace: testuser
echo spec:
echo ^  replicas: 0
echo ^  selector:
echo ^    matchLabels:
echo ^      app: testuser-api
echo ^  template:
echo ^    metadata:
echo ^      labels:
echo ^        app: testuser-api
echo ^    spec:
echo ^      serviceAccountName: testuser-bot
echo ^      securityContext:
echo ^        runAsNonRoot: true
echo ^        seccompProfile:
echo ^          type: RuntimeDefault
echo ^        fsGroup: 1000
echo ^      containers:
echo ^      - name: api
echo ^        image: caf0957b5c26acr.azurecr.io/goose-api-server:2609251236
echo ^        envFrom:
echo ^        - configMapRef:
echo ^            name: testuser-env
echo ^        ports:
echo ^        - containerPort: 3001
echo ^        securityContext:
echo ^          allowPrivilegeEscalation: false
echo ^          capabilities:
echo ^            drop:
echo ^            - ALL
echo ^          runAsUser: 1000
echo ^          runAsGroup: 1000
echo ^        resources:
echo ^          requests:
echo ^            cpu: "250m"
echo ^            memory: "512Mi"
echo ^          limits:
echo ^            cpu: "500m"
echo ^            memory: "1Gi"
) > deployment.yaml

kubectl apply -f deployment.yaml

# 6. Expose via LoadBalancer Service (direct external IP) and optional Ingress/Gateway
(
echo apiVersion: v1
echo kind: Service
echo metadata:
echo ^  name: testuser-svc
echo ^  namespace: testuser
echo spec:
echo ^  selector:
echo ^    app: testuser-api
echo ^  ports:
echo ^  - port: 80
echo ^    targetPort: 3001
echo ^  type: LoadBalancer
) > service.yaml

kubectl apply -f service.yaml

# (Optional) If an ingress controller is available, map a hostname to the service instead:

(
echo apiVersion: networking.k8s.io/v1
echo kind: Ingress
echo metadata:
echo ^  name: testuser-ingress
echo ^  namespace: testuser
echo spec:
echo ^  ingressClassName: web
echo ^  rules:
echo ^  - host: testuser.env.example.com
echo ^    http:
echo ^      paths:
echo ^      - path: /
echo ^        pathType: Prefix
echo ^        backend:
echo ^          service:
echo ^            name: testuser-svc
echo ^            port:
echo ^              number: 80
echo ^  tls:
echo ^  - hosts:
echo ^    - testuser.env.example.com
echo ^    secretName: testuser-tls
) > ingress.yaml

kubectl apply -f ingress.yaml

# 7. Activate environment when user connects
kubectl scale deployment testuser-api -n testuser --replicas=1

# 8. Fetch external access details
kubectl get service testuser-svc -n testuser -o jsonpath='{.status.loadBalancer.ingress[0].ip}'
# (or hostname if provided) and optionally the ingress hostname if configured:
kubectl get ingress testuser-ingress -n testuser -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'

# 9. Deactivate environment when user leaves
kubectl scale deployment testuser-api -n testuser --replicas=0
```

## Automation Opportunities
- **Custom Operator / Controller**: Model a `UserEnvironment` CRD that captures desired image, env vars, and access controls; reconcile to create Deployments, Services, Quotas, and scale state. https://kubernetes.io/docs/concepts/extend-kubernetes/operator/
- **GitOps**: Store per-user manifests in a Git repo and use Flux or Argo CD to reconcile; platform writes manifests on environment create/delete.
- **KEDA/Knative Hooks**: Configure HTTP or queue-based scalers that monitor activity and set replicas to zero after idle windows. https://keda.sh/docs/2.14/concepts/scaling-deployments/ https://knative.dev/docs/serving/autoscaling/autoscaler-types/#scale-to-zero
- **Azure Integrations**: Use Azure Policy to enforce namespace labels and Pod Security, and Azure Monitor/Container Insights for per-namespace logging. https://learn.microsoft.com/en-us/azure/aks/operator-best-practices-cluster-isolation

## Open Implementation Questions
1. How should we represent user projects declaratively—CRDs, GitOps manifests, or direct API calls—and which team owns the reconciliation logic?
2. What authentication flow allows the user app (or backend) to assume the correct service account using Azure AD workload identity without leaking tokens? https://learn.microsoft.com/en-us/azure/aks/workload-identity-overview
3. Do we need autoscaling to zero via KEDA/Knative, or is explicit scale orchestration sufficient for expected traffic patterns? https://keda.sh/docs/2.14/concepts/scaling-deployments/ https://knative.dev/docs/serving/autoscaling/autoscaler-types/#scale-to-zero
4. How will we store and snapshot persistent user data (PVCs, Azure Files, Blob CSI) while ensuring teardown cleans up unused volumes?
5. Should particularly untrusted workloads leverage AKS pod sandboxing or dedicated node pools with hardened policies? https://learn.microsoft.com/en-us/azure/aks/use-pod-sandboxing
6. What monitoring and alerting thresholds signal stuck activations, failed scaling, or quota exhaustion per namespace, and how do we surface those back to the AI agent?
7. If we adopt virtual clusters for stronger isolation, how do we manage the overhead (control plane cost, networking complexity) versus namespace isolation? https://www.vcluster.com/docs/architecture/what-is-a-virtual-cluster
