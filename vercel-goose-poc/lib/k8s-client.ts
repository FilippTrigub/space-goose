import * as k8s from '@kubernetes/client-node'
import yaml from 'js-yaml'
import { IProject } from './models'

interface K8sConfig {
  kubeConfigBase64?: string
  kubeHost?: string
  kubeToken?: string
  kubeCa?: string
}

export class KubernetesManager {
  private k8sApi: k8s.CoreV1Api
  private k8sAppsApi: k8s.AppsV1Api
  private k8sNetworkingApi: k8s.NetworkingV1Api
  private kc: k8s.KubeConfig

  constructor() {
    this.kc = new k8s.KubeConfig()
    this.initKubeConfig()
    
    this.k8sApi = this.kc.makeApiClient(k8s.CoreV1Api)
    this.k8sAppsApi = this.kc.makeApiClient(k8s.AppsV1Api)
    this.k8sNetworkingApi = this.kc.makeApiClient(k8s.NetworkingV1Api)
  }

  private initKubeConfig() {
    if (process.env.KUBE_CONFIG_BASE64) {
      // Load from base64 encoded kubeconfig
      const kubeConfigYaml = Buffer.from(process.env.KUBE_CONFIG_BASE64, 'base64').toString('utf8')
      this.kc.loadFromString(kubeConfigYaml)
    } else if (process.env.KUBE_HOST && process.env.KUBE_TOKEN) {
      // Load from discrete environment variables
      const cluster = {
        name: 'poc-cluster',
        server: process.env.KUBE_HOST,
        certificateAuthorityData: process.env.KUBE_CA || ''
      }
      
      const user = {
        name: 'poc-user',
        token: process.env.KUBE_TOKEN
      }
      
      const context = {
        name: 'poc-context',
        cluster: cluster.name,
        user: user.name
      }
      
      this.kc.loadFromOptions({
        clusters: [cluster],
        users: [user],
        contexts: [context],
        currentContext: context.name
      })
    } else {
      // Fallback to default (for local development)
      this.kc.loadFromDefault()
    }
  }

  async ensureNamespace(userId: string): Promise<string> {
    const namespaceName = `${process.env.KUBE_NAMESPACE_PREFIX || 'user-'}${userId}`
    
    try {
      // Check if namespace exists
      await this.k8sApi.readNamespace(namespaceName)
      return namespaceName
    } catch (error) {
      // Namespace doesn't exist, create it
      const namespace = {
        apiVersion: 'v1',
        kind: 'Namespace',
        metadata: {
          name: namespaceName,
          labels: {
            'pod-security.kubernetes.io/enforce': 'restricted',
            'pod-security.kubernetes.io/audit': 'restricted',
            'pod-security.kubernetes.io/warn': 'restricted',
            'app.kubernetes.io/managed-by': 'goose-poc'
          }
        }
      }
      
      await this.k8sApi.createNamespace(namespace)
      return namespaceName
    }
  }

  async applyProjectResources(project: IProject): Promise<void> {
    const namespace = project.namespace
    const deploymentName = `proj-${project.project_id}-api`
    const serviceName = `proj-${project.project_id}-svc`
    const ingressName = `proj-${project.project_id}-ingress`
    
    // Create Deployment
    const deployment = this.createDeploymentManifest({
      name: deploymentName,
      namespace,
      projectId: project.project_id,
      userId: project.user_id,
      image: process.env.ACR_IMAGE || 'nginx:latest' // Fallback for testing
    })
    
    try {
      await this.k8sAppsApi.createNamespacedDeployment(namespace, deployment)
    } catch (error: any) {
      if (error.response?.statusCode !== 409) { // 409 = already exists
        throw error
      }
    }
    
    // Create Service
    const service = this.createServiceManifest({
      name: serviceName,
      namespace,
      deploymentName,
      port: parseInt(process.env.GOOSE_API_PORT || '3001')
    })
    
    try {
      await this.k8sApi.createNamespacedService(namespace, service)
    } catch (error: any) {
      if (error.response?.statusCode !== 409) {
        throw error
      }
    }
    
    // Create Ingress (if base domain configured)
    if (process.env.INGRESS_BASE_DOMAIN) {
      const ingress = this.createIngressManifest({
        name: ingressName,
        namespace,
        serviceName,
        host: `proj-${project.project_id}.user-${project.user_id}.${process.env.INGRESS_BASE_DOMAIN}`,
        port: parseInt(process.env.GOOSE_API_PORT || '3001')
      })
      
      try {
        await this.k8sNetworkingApi.createNamespacedIngress(namespace, ingress)
      } catch (error: any) {
        if (error.response?.statusCode !== 409) {
          throw error
        }
      }
    }
  }

  async scaleDeployment(namespace: string, deploymentName: string, replicas: number): Promise<void> {
    const patch = {
      spec: {
        replicas
      }
    }
    
    await this.k8sAppsApi.patchNamespacedDeployment(
      deploymentName,
      namespace,
      patch,
      undefined,
      undefined,
      undefined,
      undefined,
      undefined,
      { headers: { 'Content-Type': 'application/strategic-merge-patch+json' } }
    )
  }

  async getProjectEndpoint(project: IProject): Promise<string | null> {
    const namespace = project.namespace
    const serviceName = `proj-${project.project_id}-svc`
    
    try {
      // Try to get LoadBalancer IP from Service
      const service = await this.k8sApi.readNamespacedService(serviceName, namespace)
      const loadBalancer = service.body.status?.loadBalancer
      
      if (loadBalancer?.ingress && loadBalancer.ingress.length > 0) {
        const ingress = loadBalancer.ingress[0]
        const host = ingress.ip || ingress.hostname
        if (host) {
          return `http://${host}:${process.env.GOOSE_API_PORT || 3001}`
        }
      }
      
      // Fallback: check Ingress if configured
      if (process.env.INGRESS_BASE_DOMAIN) {
        const ingressName = `proj-${project.project_id}-ingress`
        try {
          const ingress = await this.k8sNetworkingApi.readNamespacedIngress(ingressName, namespace)
          if (ingress.body.status?.loadBalancer?.ingress?.[0]) {
            const host = `proj-${project.project_id}.user-${project.user_id}.${process.env.INGRESS_BASE_DOMAIN}`
            return `http://${host}`
          }
        } catch (ingressError) {
          // Ingress not ready yet
        }
      }
      
      return null
    } catch (error) {
      console.error('Error getting project endpoint:', error)
      return null
    }
  }

  async waitForPodReady(namespace: string, deploymentName: string, timeoutMs: number = 120000): Promise<boolean> {
    const startTime = Date.now()
    
    while (Date.now() - startTime < timeoutMs) {
      try {
        const pods = await this.k8sApi.listNamespacedPod(
          namespace,
          undefined,
          undefined,
          undefined,
          undefined,
          `app=${deploymentName}`
        )
        
        const pod = pods.body.items[0]
        if (pod?.status?.phase === 'Running' && pod.status.conditions?.some(
          c => c.type === 'Ready' && c.status === 'True'
        )) {
          return true
        }
      } catch (error) {
        // Continue waiting
      }
      
      await new Promise(resolve => setTimeout(resolve, 2000)) // Wait 2 seconds
    }
    
    return false
  }

  async deleteProjectResources(project: IProject): Promise<void> {
    const namespace = project.namespace
    const deploymentName = `proj-${project.project_id}-api`
    const serviceName = `proj-${project.project_id}-svc`
    const ingressName = `proj-${project.project_id}-ingress`
    
    // Delete in reverse order
    try {
      if (process.env.INGRESS_BASE_DOMAIN) {
        await this.k8sNetworkingApi.deleteNamespacedIngress(ingressName, namespace)
      }
    } catch (error) {
      // Ignore if not found
    }
    
    try {
      await this.k8sApi.deleteNamespacedService(serviceName, namespace)
    } catch (error) {
      // Ignore if not found
    }
    
    try {
      await this.k8sAppsApi.deleteNamespacedDeployment(deploymentName, namespace)
    } catch (error) {
      // Ignore if not found
    }
  }

  private createDeploymentManifest({ name, namespace, projectId, userId, image }: {
    name: string
    namespace: string
    projectId: string
    userId: string
    image: string
  }) {
    return {
      apiVersion: 'apps/v1',
      kind: 'Deployment',
      metadata: {
        name,
        namespace,
        labels: {
          app: name,
          'app.kubernetes.io/name': 'goose-api',
          'app.kubernetes.io/managed-by': 'goose-poc',
          'project-id': projectId,
          'user-id': userId
        }
      },
      spec: {
        replicas: 0, // Start scaled down
        selector: {
          matchLabels: {
            app: name
          }
        },
        template: {
          metadata: {
            labels: {
              app: name
            }
          },
          spec: {
            securityContext: {
              runAsNonRoot: true,
              runAsUser: 1000,
              runAsGroup: 1000,
              fsGroup: 1000
            },
            containers: [{
              name: 'goose-api',
              image,
              ports: [{
                containerPort: parseInt(process.env.GOOSE_API_PORT || '3001'),
                name: 'http'
              }],
              env: [
                { name: 'USER_ID', value: userId },
                { name: 'PROJECT_ID', value: projectId },
                { name: 'PORT', value: process.env.GOOSE_API_PORT || '3001' }
              ],
              resources: {
                requests: {
                  cpu: '100m',
                  memory: '128Mi'
                },
                limits: {
                  cpu: '500m',
                  memory: '512Mi'
                }
              },
              livenessProbe: {
                httpGet: {
                  path: '/health',
                  port: 'http'
                },
                initialDelaySeconds: 30,
                periodSeconds: 10
              },
              readinessProbe: {
                httpGet: {
                  path: '/health',
                  port: 'http'
                },
                initialDelaySeconds: 5,
                periodSeconds: 5
              }
            }]
          }
        }
      }
    }
  }

  private createServiceManifest({ name, namespace, deploymentName, port }: {
    name: string
    namespace: string
    deploymentName: string
    port: number
  }) {
    return {
      apiVersion: 'v1',
      kind: 'Service',
      metadata: {
        name,
        namespace,
        labels: {
          app: deploymentName
        }
      },
      spec: {
        type: 'LoadBalancer', // For MVP - gets external IP
        selector: {
          app: deploymentName
        },
        ports: [{
          port,
          targetPort: 'http',
          protocol: 'TCP'
        }]
      }
    }
  }

  private createIngressManifest({ name, namespace, serviceName, host, port }: {
    name: string
    namespace: string
    serviceName: string
    host: string
    port: number
  }) {
    return {
      apiVersion: 'networking.k8s.io/v1',
      kind: 'Ingress',
      metadata: {
        name,
        namespace,
        annotations: {
          'nginx.ingress.kubernetes.io/rewrite-target': '/'
        }
      },
      spec: {
        rules: [{
          host,
          http: {
            paths: [{
              path: '/',
              pathType: 'Prefix',
              backend: {
                service: {
                  name: serviceName,
                  port: {
                    number: port
                  }
                }
              }
            }]
          }
        }]
      }
    }
  }
}
