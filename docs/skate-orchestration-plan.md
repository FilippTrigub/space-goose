Title: Skate Orchestration – Research, Cloud Fit, and Azure Plan

Status
- Network-restricted environment prevented reading upstream docs now.
- This plan outlines how we will use Skate, how to validate Azure support, and concrete next steps. Replace TODOs once docs are accessible.

Summary (Assumptions until verified)
- Skate appears to be a container orchestration tool aiming for simpler ops than full Kubernetes.
- Likely operates on standard Linux hosts with Docker/Containerd.
- If it is host/VM oriented, it should run on any cloud that provides Linux VMs (Azure, AWS, GCP, etc.). If it’s a control-plane for K8s, then it targets any managed K8s (AKS/EKS/GKE).

Key Questions To Confirm (from repo)
- Installation: prerequisites (Docker, Containerd, specific Linux distros), install method (curl script, binary, Helm, etc.).
- Scope: single-node vs multi-node support; scheduling, autoscaling, service discovery, ingress, secrets, volumes.
- Networking: ingress solution, LB requirements, supported CNIs (if relevant).
- Storage: how persistent volumes are managed.
- Auth/identity: integrations (OIDC, cloud IAM) if any.
- Observability: built-in logs/metrics/traces; integrations (Prometheus/Grafana/ELK).
- Configuration: declarative format (YAML), CLI, or API.
- Cloud specifics: any documented examples for Azure/AWS/GCP.

How To Use Skate (verified from Getting Started)
1) Install prerequisites on a Linux host (Ubuntu 22.04 LTS recommended):
   - Docker (24.x+) or Containerd, curl, systemd.
2) Install Skate CLI
   - `curl -sL https://raw.githubusercontent.com/skateco/skate/refs/heads/main/hack/install-skate.sh | bash`
3) Optional: Install Skate-in-Docker (sind) for a local cluster
   - `curl -sL https://raw.githubusercontent.com/skateco/skate/refs/heads/main/hack/install-sind.sh | bash`
   - Create local cluster: `sind create --ssh-private-key ~/.ssh/<private_key> --ssh-public-key ~/.ssh/<public_key>`
   - Recreate if needed: `sind remove && sind create ...`
4) Manual cluster creation (equivalent to what sind automates)
   - Create cluster and set context:
     - `skate create cluster my-cluster --default-user <ssh_user> --default-key ~/.ssh/<ssh_public_key>`
     - `skate config use-context my-cluster`
   - Add nodes (example for two nodes):
     - `skate create node --name node-1 --subnet-cidr 20.1.0.0/16 --host <node1_ip> --peer-host <node1_ip_from_peers>`
     - `skate create node --name node-2 --subnet-cidr 20.2.0.0/16 --host <node2_ip> --peer-host <node2_ip_from_peers>`
5) Deploy a sample app (Kubernetes-style manifests via Skate)
   - Deployment (nginx, 2 replicas):
     - `cat <<'EOF' | skate apply -f -`
       ---
       apiVersion: apps/v1
       kind: Deployment
       metadata:
         name: nginx
         namespace: my-app
       spec:
         replicas: 2
         template:
           spec:
             containers:
             - name: nginx
               image: nginx:1.14.2
       EOF
   - Check deployment: `skate get deployment`
   - Service:
     - `cat <<'EOF' | skate apply -f -`
       ---
       apiVersion: v1
       kind: Service
       metadata:
         name: nginx
         namespace: my-app
       spec:
         selector:
           app.kubernetes.io/name: nginx
         ports:
         - protocol: TCP
           port: 80
           targetPort: 80
       EOF
     - `skate get service`
   - Ingress:
     - `cat <<'EOF' | skate apply -f -`
       apiVersion: networking.k8s.io/v1
       kind: Ingress
       metadata:
         name: public
         namespace: my-app
         annotations:
           nginx.ingress.kubernetes.io/ssl-redirect: "false"
       spec:
         rules:
         - host: nginx.example.com
           http:
             paths:
             - path: /
               pathType: Prefix
               backend:
                 service:
                   name: nginx.my-app
                   port:
                     number: 80
       EOF`
   - Test (replace with a node IP): `curl --header "Host: nginx.example.com" --insecure http://<NODE_IP>`

Cloud Suitability
- Azure
  - Fit: Strong, if Skate runs directly on Linux VMs or on AKS.
  - Networking: Use Azure Load Balancer + Public IP; NSGs for port access.
  - Storage: Azure Disks/Files if Skate integrates with CSI; otherwise hostPath or managed disks mounted to VMs.
  - Identity: Azure AD/OIDC if supported; otherwise local auth.
  - Observability: Azure Monitor/Log Analytics or open-source stack.
- AWS
  - Fit: Similar to Azure; use EC2 + ALB/NLB, EBS/EFS, CloudWatch.
- GCP
  - Fit: Similar; use GCE + Load Balancer, PD/Filestore, Cloud Logging/Monitoring.

Does Skate Work With Azure?
- Yes: Skate provisions/controls nodes over SSH and schedules containers across hosts. Azure VMs work well as nodes when reachable over a private network with inter-node traffic allowed. The steps below show how to stand this up.

Azure Deployment (VMs as Skate nodes)
1) Create resource group and virtual network
   - `az group create -n rg-skate -l eastus`
   - `az network vnet create -g rg-skate -n vnet-skate --address-prefixes 10.10.0.0/16 --subnet-name sn-skate --subnet-prefix 10.10.1.0/24`
   - `az network nsg create -g rg-skate -n nsg-skate`
   - Allow inbound SSH/HTTP/HTTPS to nodes (adjust as needed):
     - `az network nsg rule create -g rg-skate --nsg-name nsg-skate -n allow-ssh --priority 1000 --destination-port-ranges 22 --access Allow --protocol Tcp --direction Inbound`
     - `az network nsg rule create -g rg-skate --nsg-name nsg-skate -n allow-http --priority 1010 --destination-port-ranges 80 --access Allow --protocol Tcp --direction Inbound`
     - `az network nsg rule create -g rg-skate --nsg-name nsg-skate -n allow-https --priority 1020 --destination-port-ranges 443 --access Allow --protocol Tcp --direction Inbound`
   - Recommend: allow all traffic within the virtual network (intra-subnet) so nodes can communicate:
     - `az network nsg rule create -g rg-skate --nsg-name nsg-skate -n allow-internal --priority 1100 --source-address-prefixes VirtualNetwork --destination-address-prefixes VirtualNetwork --access Allow --protocol '*' --direction Inbound`
2) Create two Ubuntu VMs in the same subnet
   - `az vm create -g rg-skate -n node-1 -l eastus --image Ubuntu2204 --size Standard_D2s_v5 --vnet-name vnet-skate --subnet sn-skate --public-ip-sku Standard --nsg nsg-skate --admin-username azureuser --generate-ssh-keys`
   - `az vm create -g rg-skate -n node-2 -l eastus --image Ubuntu2204 --size Standard_D2s_v5 --vnet-name vnet-skate --subnet sn-skate --public-ip-sku Standard --nsg nsg-skate --admin-username azureuser --generate-ssh-keys`
   - Get private IPs (used for host/peer-host):
     - `az vm list-ip-addresses -g rg-skate -n node-1 --query "[0].virtualMachine.network.privateIpAddresses[0]" -o tsv`
     - `az vm list-ip-addresses -g rg-skate -n node-2 --query "[0].virtualMachine.network.privateIpAddresses[0]" -o tsv`
   - Optional: get public IPs for initial SSH/testing
     - `az vm show -d -g rg-skate -n node-1 --query publicIps -o tsv`
     - `az vm show -d -g rg-skate -n node-2 --query publicIps -o tsv`
3) Install Docker and Skate on each VM (one-time)
   - SSH: `ssh azureuser@<NODE_PUBLIC_IP>`
   - Docker Engine (Ubuntu):
     - `sudo apt-get update && sudo apt-get install -y ca-certificates curl gnupg`
     - `sudo install -m 0755 -d /etc/apt/keyrings`
     - `curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg`
     - `echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null`
     - `sudo apt-get update && sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin`
     - `sudo usermod -aG docker $USER && newgrp docker`
   - Install Skate CLI on your control machine (not required on nodes if Skate SSHes in):
     - `curl -sL https://raw.githubusercontent.com/skateco/skate/refs/heads/main/hack/install-skate.sh | bash`
4) Create the Skate cluster from your control machine
   - Ensure your SSH public key and agent are configured, and the user is `azureuser`.
   - `skate create cluster my-azure --default-user azureuser --default-key ~/.ssh/id_rsa.pub`
   - `skate config use-context my-azure`
5) Add Azure VMs as nodes (use their private IPs for intra-VNet reachability)
   - Suppose: node-1 private IP is 10.10.1.4; node-2 private IP is 10.10.1.5
   - `skate create node --name node-1 --subnet-cidr 20.1.0.0/16 --host 10.10.1.4 --peer-host 10.10.1.4`
   - `skate create node --name node-2 --subnet-cidr 20.2.0.0/16 --host 10.10.1.5 --peer-host 10.10.1.5`
   - Verify: `skate get nodes`
6) Deploy your workload and test
   - Use the Deployment/Service/Ingress example above with `skate apply`.
   - For public access, either:
     - Open port 80/443 on one node’s public IP and use its address; or
     - Create an Azure Load Balancer with both nodes as backends:
       - `az network public-ip create -g rg-skate -n pip-skate --sku Standard`
       - `az network lb create -g rg-skate -n lb-skate --sku Standard --public-ip-address pip-skate --backend-pool-name bp-skate`
       - Create health probe on port 80: `az network lb probe create -g rg-skate --lb-name lb-skate -n http-80 --protocol tcp --port 80`
       - Add LB rule: `az network lb rule create -g rg-skate --lb-name lb-skate -n http --protocol Tcp --frontend-port 80 --backend-port 80 --frontend-ip-name LoadBalancerFrontEnd --backend-pool-name bp-skate --probe-name http-80`
       - Add VMs to backend pool (bind NIC IP configs):
         - Get NIC names: `az vm show -g rg-skate -n node-1 --query 'networkProfile.networkInterfaces[0].id' -o tsv | xargs -I{} basename {}` (repeat for node-2)
         - `az network nic ip-config address-pool add -g rg-skate --nic-name <NIC_NODE1> --ip-config-name ipconfig1 --lb-name lb-skate --address-pool bp-skate`
         - `az network nic ip-config address-pool add -g rg-skate --nic-name <NIC_NODE2> --ip-config-name ipconfig1 --lb-name lb-skate --address-pool bp-skate`
       - Get LB public IP: `az network public-ip show -g rg-skate -n pip-skate --query ipAddress -o tsv`
       - Test: `curl --header "Host: nginx.example.com" http://<LB_PUBLIC_IP>`

Note on AKS
- Skate provides its own orchestration semantics and CLI; AKS is not required. If you already run AKS, continue using `kubectl`. Use Skate on raw Azure VMs when you want a lighter-weight control over hosts.

Operational Considerations
- High availability: multi-node setup, failover tests.
- Upgrades: rolling updates for Skate control components.
- Backups: config/state backups (etcd or equivalents, if used).
- Security: restrict management ports; use TLS; secrets management approach.
- Cost: estimate VM sizes, LB, storage, bandwidth.

Deliverables After Repo Review (replace TODOs)
- Confirmed install steps for Ubuntu + Docker.
- Minimal reference architecture diagram for Azure.
- Example deployment manifest/CLI command for a sample web app.
- Terraform/Bicep snippets to spin up Azure infra quickly.

Next Actions
1) Fetch and review https://github.com/skateco/skate README and docs.
2) Replace TODOs and assumptions in this file with concrete commands.
3) Build a minimal PoC on Azure (single VM), then consider HA.
4) Optionally add IaC and CI/CD wiring.

Alternatives: Per-User Containers With Minimal Complexity
- Recommendation: Azure Container Instances (ACI)
  - Why: Simplest managed way on Azure to run one long‑lived container per user without running a full orchestrator. You can create, exec into, stop, and delete each user’s container via `az container` commands. No nodes/cluster to manage.
  - Model: One ACI container group per user, 1 container inside. Optionally mount Azure File share for per‑user storage and attach to a VNet for private access.

ACI – Quick Start (Public IP + DNS)
1) Resource group
   - `az group create -n rg-users -l eastus`
2) Per‑user container (example)
   - `USER_ID=alice`
   - `az container create -g rg-users -n user-$USER_ID \
       --image YOUR_IMAGE:TAG \
       --cpu 1 --memory 2 \
       --ports 80 \
       --ip-address Public \
       --dns-name-label user-${USER_ID}-$RANDOM \
       --environment-variables USER_ID=$USER_ID`
   - Get FQDN: `az container show -g rg-users -n user-$USER_ID --query ipAddress.fqdn -o tsv`
   - Logs: `az container logs -g rg-users -n user-$USER_ID`
   - Exec/shell: `az container exec -g rg-users -n user-$USER_ID --exec-command "/bin/sh"`
   - Stop/delete: `az container stop -g rg-users -n user-$USER_ID` / `az container delete -g rg-users -n user-$USER_ID -y`

ACI – Persist Per‑User Data (Azure Files)
1) Create storage + file share
   - `az storage account create -g rg-users -n mystorage$RANDOM -l eastus --sku Standard_LRS`
   - `SA=$(az storage account list -g rg-users --query "[0].name" -o tsv)`
   - `KEY=$(az storage account keys list -g rg-users -n $SA --query "[0].value" -o tsv)`
   - `az storage share-rm create --storage-account $SA --name user-$USER_ID`
2) Create container with volume mount
   - `az container create -g rg-users -n user-$USER_ID \
       --image YOUR_IMAGE:TAG --cpu 1 --memory 2 \
       --ports 80 --ip-address Public --dns-name-label user-${USER_ID}-$RANDOM \
       --azure-file-volume-share-name user-$USER_ID \
       --azure-file-volume-account-name $SA \
       --azure-file-volume-account-key $KEY \
       --azure-file-volume-mount-path /data \
       --environment-variables USER_ID=$USER_ID DATA_DIR=/data`

ACI – Private Networking (VNet integration)
1) Create VNet + delegated subnet
   - `az network vnet create -g rg-users -n vnet-users --address-prefixes 10.20.0.0/16 --subnet-name sn-aci --subnet-prefix 10.20.1.0/24`
   - `az network vnet subnet update -g rg-users --vnet-name vnet-users -n sn-aci --delegations Microsoft.ContainerInstance/containerGroups`
2) Create container into that subnet (no public IP)
   - `az container create -g rg-users -n user-$USER_ID \
       --image YOUR_IMAGE:TAG --cpu 1 --memory 2 \
       --subnet vnet-users/sn-aci \
       --restart-policy Always \
       --environment-variables USER_ID=$USER_ID`

ACI – Per‑User Lifecycle Helpers
- Create user container function (bash)
  - `create_user() { local uid="$1"; az container create -g rg-users -n user-$uid --image YOUR_IMAGE:TAG --cpu 1 --memory 2 --ip-address Public --dns-name-label user-${uid}-$RANDOM --ports 80 --environment-variables USER_ID=$uid; }`
- Delete user container
  - `delete_user() { local uid="$1"; az container delete -g rg-users -n user-$uid -y; }`
- Exec into user container
  - `exec_user() { local uid="$1"; az container exec -g rg-users -n user-$uid --exec-command "/bin/sh"; }`

Pros/Cons of ACI
- Pros: No control plane to manage; per‑user isolation is a first‑class object; fast to create; simple CLI; integrates with Azure Files and VNets.
- Cons: Cold start on creation; per‑instance billing; limited advanced scheduling; single region per instance.

Other Straightforward Options (brief)
- Docker on a Single VM
  - Very simple: `docker run --name user-<id> -d -p <port>:<port> YOUR_IMAGE`
  - Best for small scale or PoC; you handle port assignment, cleanup, and resource limits. Can be automated with a small API that calls Docker Engine API.
- Docker Swarm
  - Easier than Kubernetes, supports multi‑host. Create a service per user: `docker service create --name user-<id> --replicas 1 YOUR_IMAGE`. Simpler ops, but ecosystem is quieter.
- Fly.io Machines
  - One “machine” (container VM) per user via CLI/API; global anycast and simple networking. Great DX, limited to Fly’s platform. Source: https://fly.io/docs/machines/
- AWS ECS Fargate
  - Serverless containers; one task per user. Slightly more setup (task defs, security groups). Good if you’re on AWS. Source: https://docs.aws.amazon.com/AmazonECS/latest/developerguide/Welcome.html
- Azure Container Apps
  - Managed app platform. Good for HTTP/event‑driven scale. Mapping “one replica per user” is not first‑class; you’d create one app per user (manageable with IaC) or use sticky routing—more complexity than ACI for this use case.

Operating the “1 container per user” model
- Identity mapping: map your user ID to the ACI resource name (e.g., `user-<id>`). Store the ACI resource ID and FQDN in your app DB.
- Access: For public endpoints, rely on `--dns-name-label` per container or place everything behind an Azure Application Gateway/ALB or API gateway that routes `Host` header to the correct user container.
- Limits: Use appropriate `--cpu/--memory` to constrain each user. Consider `--restart-policy Always` for resiliency.
- Cleanup: Garbage collect idle users via your app logic or scheduled jobs that stop or delete ACI groups after inactivity.

Sources (Alternatives)
- Azure Container Instances – Overview: https://learn.microsoft.com/azure/container-instances/container-instances-overview
- ACI Create via CLI: https://learn.microsoft.com/azure/container-instances/container-instances-quickstart
- ACI Exec/Logs: https://learn.microsoft.com/azure/container-instances/container-instances-exec and https://learn.microsoft.com/azure/container-instances/container-instances-view-logs
- ACI VNet integration: https://learn.microsoft.com/azure/container-instances/container-instances-vnet
- ACI Azure Files volume: https://learn.microsoft.com/azure/container-instances/container-instances-volume-azure-files
- Docker Swarm Mode: https://docs.docker.com/engine/swarm/
- Fly Machines: https://fly.io/docs/machines/
- AWS ECS Fargate: https://docs.aws.amazon.com/AmazonECS/latest/developerguide/Welcome.html

Azure Deployment – Commands
- Prerequisites
  - Install Azure CLI and login: `az login`
  - Set subscription: `az account set --subscription <SUBSCRIPTION_ID_OR_NAME>`

Option A: Single VM (generic Linux host)
1) Create resource group and network
   - `az group create -n rg-skate -l eastus`
   - `az network nsg create -g rg-skate -n nsg-skate`
   - Allow common ports (SSH/HTTP/HTTPS); add others as needed:
     - `az network nsg rule create -g rg-skate --nsg-name nsg-skate -n allow-ssh --priority 1000 --destination-port-ranges 22 --access Allow --protocol Tcp --direction Inbound`
     - `az network nsg rule create -g rg-skate --nsg-name nsg-skate -n allow-http --priority 1010 --destination-port-ranges 80 --access Allow --protocol Tcp --direction Inbound`
     - `az network nsg rule create -g rg-skate --nsg-name nsg-skate -n allow-https --priority 1020 --destination-port-ranges 443 --access Allow --protocol Tcp --direction Inbound`
2) Create VM (Ubuntu 22.04)
   - `az vm create -g rg-skate -n vm-skate -l eastus --image Ubuntu2204 --size Standard_D2s_v5 --public-ip-sku Standard --admin-username azureuser --generate-ssh-keys --nsg nsg-skate`
   - Get public IP: `az vm show -d -g rg-skate -n vm-skate --query publicIps -o tsv`
3) SSH to VM and install runtime
   - `ssh azureuser@<PUBLIC_IP>`
   - Docker Engine install (Ubuntu):
     - `sudo apt-get update && sudo apt-get install -y ca-certificates curl gnupg`
     - `sudo install -m 0755 -d /etc/apt/keyrings`
     - `curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg`
     - `echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null`
     - `sudo apt-get update && sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin`
     - `sudo usermod -aG docker $USER && newgrp docker`
4) Install Skate (fill in once docs are available)
   - Placeholder: `curl -fsSL <skate_install_url> | sudo bash` OR download binary and place in `/usr/local/bin`.
5) Deploy a sample app (until Skate docs are confirmed, use Docker to validate network)
   - `docker run -d --name web -p 80:80 nginx:alpine`
   - Test from local: `curl http://<PUBLIC_IP>`

Option B: AKS (Kubernetes) – recommended if Skate integrates with K8s
1) Create resource group
   - `az group create -n rg-skate-aks -l eastus`
2) Create AKS cluster (system nodepool, 1–3 nodes)
   - `az aks create -g rg-skate-aks -n aks-skate --node-count 2 --node-vm-size Standard_D4s_v5 --generate-ssh-keys`
3) Get kubeconfig
   - `az aks get-credentials -g rg-skate-aks -n aks-skate --overwrite-existing`
4) Verify access
   - `kubectl get nodes`
5) Install Skate on AKS (if Skate ships a Helm chart or manifests)
   - Placeholder Helm example: `helm repo add skate https://skateco.github.io/skate && helm install skate skate/skate -n skate-system --create-namespace`
   - Or: `kubectl apply -f https://raw.githubusercontent.com/skateco/skate/main/deploy.yaml`
6) Deploy a sample app and expose it
   - `kubectl create deployment web --image=nginx:alpine`
   - `kubectl expose deployment web --port=80 --type=LoadBalancer`
   - `kubectl get svc web -w` (wait for `EXTERNAL-IP`)
   - Test: `curl http://<EXTERNAL-IP>`

Managing Pods on AKS (control, create, SSH/exec)
Pod and Workload Control with Skate
- List, inspect
  - `skate get nodes`
  - `skate get pods -A`
  - `skate describe pod <POD> -n <NAMESPACE>`
- Create a new pod
  - Imperative-style (if supported): `skate run demo --image=nginx:alpine --port=80`
  - Declarative (pod.yaml):
    apiVersion: v1
    kind: Pod
    metadata:
      name: demo
      namespace: my-app
    spec:
      containers:
      - name: web
        image: nginx:alpine
        ports:
        - containerPort: 80
    Apply: `skate apply -f pod.yaml`
- Exec/“SSH” into a container
  - `skate exec -it <POD> -n <NAMESPACE> -- /bin/sh` (or `/bin/bash`)
- Logs, copy, port-forward
  - `skate logs -f <POD> -n <NAMESPACE>`
  - `skate cp <NAMESPACE>/<POD>:<PATH_IN_POD> <LOCAL_PATH>`
  - `skate port-forward pod/<POD> 8080:80 -n <NAMESPACE>`
- Delete or restart
  - Delete pod: `skate delete pod <POD> -n <NAMESPACE>`
  - Restart deployment: `skate rollout restart deploy/<DEPLOYMENT> -n <NAMESPACE>`

SSH Into Nodes (Azure VMs)
- `ssh azureuser@<NODE_PUBLIC_IP>` or via Bastion.
- Ensure your SSH public key is what Skate and the VMs are configured to use.

SSH Into AKS Nodes (when needed)
- Get node resource group: `az aks show -g rg-skate-aks -n aks-skate --query nodeResourceGroup -o tsv`
- Enable node SSH via VMSS if required (AKS manages VMSS); recommended path is `kubectl debug` over node SSH.
- If you must SSH, locate the VMSS and use Azure Bastion or assign a public IP per Azure guidance.

Sources
- Skate Getting Started: https://skateco.github.io/docs/getting-started/
- Skate install script: https://raw.githubusercontent.com/skateco/skate/refs/heads/main/hack/install-skate.sh
- Skate sind install: https://raw.githubusercontent.com/skateco/skate/refs/heads/main/hack/install-sind.sh
- Azure CLI install: https://learn.microsoft.com/azure/cli/azure-cli-install
- Create a Linux VM: https://learn.microsoft.com/azure/virtual-machines/linux/quick-create-portal and https://learn.microsoft.com/azure/virtual-machines/linux/quick-create-cli
- Docker Engine on Ubuntu: https://docs.docker.com/engine/install/ubuntu/
- AKS quickstart with `az aks`: https://learn.microsoft.com/azure/aks/learn/quick-kubernetes-deploy-cli
- kubectl cheatsheet: https://kubernetes.io/docs/reference/kubectl/cheatsheet/
- kubectl exec/logs/cp: https://kubernetes.io/docs/tasks/debug/debug-application/
- Ephemeral containers (kubectl debug): https://kubernetes.io/docs/tasks/debug/debug-application/debug-running-pod/#ephemeral-container
- AKS connect and credentials: https://learn.microsoft.com/azure/aks/learn/quick-kubernetes-deploy-cli#get-credentials
 - Azure Load Balancer: https://learn.microsoft.com/azure/load-balancer/load-balancer-overview
