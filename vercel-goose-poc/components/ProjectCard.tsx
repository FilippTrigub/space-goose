'use client'

import { useState } from 'react'
import { IProject } from '@/lib/models'
import Link from 'next/link'

interface ProjectCardProps {
  project: IProject
  userId: string
  onProjectDeleted: (projectId: string) => void
  onProjectUpdated: (project: IProject) => void
}

const statusColors = {
  inactive: 'bg-gray-100 text-gray-800',
  activating: 'bg-blue-100 text-blue-800',
  active: 'bg-green-100 text-green-800',
  deactivating: 'bg-yellow-100 text-yellow-800',
  error: 'bg-red-100 text-red-800'
}

const statusDescriptions = {
  inactive: 'Pod scaled to 0',
  activating: 'Creating K8s resources...',
  active: 'Pod running and ready',
  deactivating: 'Scaling down...',
  error: 'Deployment failed'
}

export default function ProjectCard({ project, userId, onProjectDeleted, onProjectUpdated }: ProjectCardProps) {
  const [activating, setActivating] = useState(false)
  const [deactivating, setDeactivating] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [error, setError] = useState('')
  const [logs, setLogs] = useState<string[]>([])

  const handleActivate = async () => {
    try {
      setActivating(true)
      setError('')
      setLogs([])
      
      const response = await fetch(`/api/users/${userId}/projects/${project.project_id}/activate`, {
        method: 'POST'
      })
      
      const data = await response.json()
      
      if (!response.ok) {
        throw new Error(data.error || 'Failed to activate project')
      }
      
      setLogs(data.logs || [])
      onProjectUpdated(data.project)
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to activate project')
    } finally {
      setActivating(false)
    }
  }

  const handleDeactivate = async () => {
    try {
      setDeactivating(true)
      setError('')
      
      const response = await fetch(`/api/users/${userId}/projects/${project.project_id}/deactivate`, {
        method: 'POST'
      })
      
      const data = await response.json()
      
      if (!response.ok) {
        throw new Error(data.error || 'Failed to deactivate project')
      }
      
      setLogs(data.logs || [])
      onProjectUpdated(data.project)
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to deactivate project')
    } finally {
      setDeactivating(false)
    }
  }

  const handleDelete = async () => {
    if (!confirm('Are you sure you want to delete this project? This will remove all Kubernetes resources.')) {
      return
    }

    try {
      setDeleting(true)
      
      const response = await fetch(`/api/users/${userId}/projects/${project.project_id}`, {
        method: 'DELETE'
      })
      
      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.error || 'Failed to delete project')
      }
      
      onProjectDeleted(project.project_id)
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete project')
    } finally {
      setDeleting(false)
    }
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
      {/* Header */}
      <div className="flex justify-between items-start mb-4">
        <div>
          <h3 className="text-lg font-medium text-gray-900">{project.name}</h3>
          {project.description && (
            <p className="text-sm text-gray-600 mt-1">{project.description}</p>
          )}
          <div className="mt-2 text-xs text-gray-500">
            <span className="font-mono">{project.namespace}</span> • <span className="font-mono">{project.deployment}</span>
          </div>
        </div>
        <div className="text-right">
          <span className={`px-3 py-1 rounded-full text-xs font-medium ${statusColors[project.status]}`}>
            {project.status.charAt(0).toUpperCase() + project.status.slice(1)}
          </span>
          <div className="text-xs text-gray-500 mt-1">
            {statusDescriptions[project.status]}
          </div>
        </div>
      </div>

      {/* Error Display */}
      {(error || project.error_message) && (
        <div className="bg-red-50 border border-red-200 rounded-md p-3 mb-4">
          <div className="text-red-800 text-sm">
            <strong>Error:</strong> {error || project.error_message}
          </div>
        </div>
      )}

      {/* Logs Display */}
      {logs.length > 0 && (
        <div className="bg-gray-50 border border-gray-200 rounded-md p-3 mb-4">
          <div className="text-xs text-gray-700">
            <strong>Activation Logs:</strong>
            <div className="mt-1 space-y-1 max-h-24 overflow-y-auto">
              {logs.map((log, index) => (
                <div key={index} className="font-mono text-xs">{log}</div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Kubernetes Info */}
      {project.endpoint && (
        <div className="bg-blue-50 border border-blue-200 rounded-md p-3 mb-4">
          <div className="text-blue-800 text-sm">
            <strong>Endpoint:</strong> 
            <a href={project.endpoint} target="_blank" rel="noopener noreferrer" className="ml-2 font-mono text-xs underline">
              {project.endpoint}
            </a>
          </div>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex gap-2 mt-4">
        {project.status === 'inactive' && (
          <button
            onClick={handleActivate}
            disabled={activating}
            className="bg-blue-600 text-white px-4 py-2 text-sm rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {activating ? 'Activating...' : 'Activate'}
          </button>
        )}

        {project.status === 'error' && (
          <button
            onClick={handleActivate}
            disabled={activating}
            className="bg-blue-600 text-white px-4 py-2 text-sm rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {activating ? 'Retrying...' : 'Retry Activation'}
          </button>
        )}

        {project.status === 'active' && (
          <>
            <button
              onClick={handleDeactivate}
              disabled={deactivating}
              className="bg-yellow-600 text-white px-4 py-2 text-sm rounded-md hover:bg-yellow-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {deactivating ? 'Deactivating...' : 'Deactivate'}
            </button>
            <Link
              href={`/chat/${userId}/${project.project_id}`}
              className="bg-green-600 text-white px-4 py-2 text-sm rounded-md hover:bg-green-700 transition-colors inline-block"
            >
              Chat with Goose
            </Link>
          </>
        )}

        <button
          onClick={handleDelete}
          disabled={deleting || activating || deactivating}
          className="bg-red-600 text-white px-4 py-2 text-sm rounded-md hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors ml-auto"
        >
          {deleting ? 'Deleting...' : 'Delete'}
        </button>
      </div>

      {/* Timing Info */}
      {(project.last_activated_at || project.last_deactivated_at) && (
        <div className="mt-4 pt-3 border-t border-gray-200">
          <div className="text-xs text-gray-500 space-y-1">
            {project.last_activated_at && (
              <div>
                <strong>Last Activated:</strong> {new Date(project.last_activated_at).toLocaleString()}
              </div>
            )}
            {project.last_deactivated_at && (
              <div>
                <strong>Last Deactivated:</strong> {new Date(project.last_deactivated_at).toLocaleString()}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
