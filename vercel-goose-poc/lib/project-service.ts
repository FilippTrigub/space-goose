import { v4 as uuidv4 } from 'uuid'
import { Project, IProject } from './models'
import { KubernetesManager } from './k8s-client'
import { connectDB } from './db'

export class ProjectService {
  private k8sManager: KubernetesManager

  constructor() {
    this.k8sManager = new KubernetesManager()
  }

  async createProject(userId: string, name: string, description: string = ''): Promise<IProject> {
    await connectDB()
    
    const projectId = uuidv4()
    const namespace = `${process.env.KUBE_NAMESPACE_PREFIX || 'user-'}${userId}`
    
    // Ensure namespace exists
    await this.k8sManager.ensureNamespace(userId)
    
    const project = new Project({
      _id: uuidv4(),
      user_id: userId,
      project_id: projectId,
      name,
      description,
      namespace,
      deployment: `proj-${projectId}-api`,
      service: `proj-${projectId}-svc`,
      ingress: process.env.INGRESS_BASE_DOMAIN ? `proj-${projectId}-ingress` : undefined,
      status: 'inactive'
    })
    
    await project.save()
    return project.toObject()
  }

  async activateProject(userId: string, projectId: string): Promise<{ project: IProject; logs: string[] }> {
    await connectDB()
    
    const logs: string[] = []
    
    const project = await Project.findOne({ 
      user_id: userId, 
      project_id: projectId 
    })
    
    if (!project) {
      throw new Error('Project not found')
    }
    
    if (project.status === 'active') {
      return { project: project.toObject(), logs: ['Project already active'] }
    }
    
    try {
      // Update status to activating
      project.status = 'activating'
      project.error_message = undefined
      await project.save()
      logs.push('Setting project status to activating...')
      
      // Ensure namespace exists
      logs.push('Ensuring namespace exists...')
      await this.k8sManager.ensureNamespace(userId)
      logs.push(`Namespace ${project.namespace} ready`)
      
      // Apply Kubernetes resources
      logs.push('Applying Kubernetes manifests...')
      await this.k8sManager.applyProjectResources(project.toObject())
      logs.push('Kubernetes resources created')
      
      // Scale deployment to 1
      logs.push('Scaling deployment to 1 replica...')
      await this.k8sManager.scaleDeployment(project.namespace, project.deployment!, 1)
      logs.push('Deployment scaled up')
      
      // Wait for pod to be ready
      logs.push('Waiting for pod to be ready...')
      const isReady = await this.k8sManager.waitForPodReady(project.namespace, project.deployment!, 120000)
      
      if (!isReady) {
        throw new Error('Pod failed to become ready within timeout')
      }
      logs.push('Pod is ready')
      
      // Get endpoint
      logs.push('Retrieving project endpoint...')
      const endpoint = await this.k8sManager.getProjectEndpoint(project.toObject())
      
      if (!endpoint) {
        // For POC, we can use port-forward as fallback
        logs.push('No external endpoint found, will need port-forward for access')
      } else {
        logs.push(`Project endpoint: ${endpoint}`)
      }
      
      // Update project status
      project.status = 'active'
      project.endpoint = endpoint || undefined
      project.last_activated_at = new Date()
      await project.save()
      logs.push('Project activated successfully')
      
      return { project: project.toObject(), logs }
      
    } catch (error) {
      // Update project with error status
      project.status = 'error'
      project.error_message = error instanceof Error ? error.message : 'Unknown error'
      await project.save()
      
      logs.push(`Error: ${error instanceof Error ? error.message : 'Unknown error'}`)
      throw error
    }
  }

  async deactivateProject(userId: string, projectId: string): Promise<{ project: IProject; logs: string[] }> {
    await connectDB()
    
    const logs: string[] = []
    
    const project = await Project.findOne({ 
      user_id: userId, 
      project_id: projectId 
    })
    
    if (!project) {
      throw new Error('Project not found')
    }
    
    if (project.status === 'inactive') {
      return { project: project.toObject(), logs: ['Project already inactive'] }
    }
    
    try {
      // Update status to deactivating
      project.status = 'deactivating'
      await project.save()
      logs.push('Setting project status to deactivating...')
      
      // Scale deployment to 0
      logs.push('Scaling deployment to 0 replicas...')
      await this.k8sManager.scaleDeployment(project.namespace, project.deployment!, 0)
      logs.push('Deployment scaled down')
      
      // Update project status
      project.status = 'inactive'
      project.endpoint = undefined
      project.last_deactivated_at = new Date()
      await project.save()
      logs.push('Project deactivated successfully')
      
      return { project: project.toObject(), logs }
      
    } catch (error) {
      // Update project with error status
      project.status = 'error'
      project.error_message = error instanceof Error ? error.message : 'Unknown error'
      await project.save()
      
      logs.push(`Error: ${error instanceof Error ? error.message : 'Unknown error'}`)
      throw error
    }
  }

  async deleteProject(userId: string, projectId: string): Promise<void> {
    await connectDB()
    
    const project = await Project.findOne({ 
      user_id: userId, 
      project_id: projectId 
    })
    
    if (!project) {
      throw new Error('Project not found')
    }
    
    // First deactivate if active
    if (project.status === 'active') {
      await this.deactivateProject(userId, projectId)
    }
    
    // Delete Kubernetes resources
    await this.k8sManager.deleteProjectResources(project.toObject())
    
    // Delete from database
    await Project.deleteOne({ _id: project._id })
  }

  async getProjects(userId: string): Promise<IProject[]> {
    await connectDB()
    
    const projects = await Project.find({ user_id: userId })
      .sort({ created_at: -1 })
    
    return projects.map(p => p.toObject())
  }
}
