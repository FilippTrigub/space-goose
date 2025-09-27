'use client'

import { useState, useEffect } from 'react'
import { IProject } from '@/lib/models'
import ProjectCard from './ProjectCard'
import CreateProjectForm from './CreateProjectForm'

interface ProjectListProps {
  userId: string
}

export default function ProjectList({ userId }: ProjectListProps) {
  const [projects, setProjects] = useState<IProject[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string>('')
  const [showCreateForm, setShowCreateForm] = useState(false)

  useEffect(() => {
    fetchProjects()
  }, [userId])

  const fetchProjects = async () => {
    try {
      setLoading(true)
      const response = await fetch(`/api/users/${userId}/projects`)
      if (!response.ok) throw new Error('Failed to fetch projects')
      const data = await response.json()
      setProjects(data.projects)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load projects')
    } finally {
      setLoading(false)
    }
  }

  const handleProjectCreated = (newProject: IProject) => {
    setProjects(prev => [newProject, ...prev])
    setShowCreateForm(false)
  }

  const handleProjectDeleted = (projectId: string) => {
    setProjects(prev => prev.filter(p => p.project_id !== projectId))
  }

  const handleProjectUpdated = (updatedProject: IProject) => {
    setProjects(prev => prev.map(p => 
      p.project_id === updatedProject.project_id ? updatedProject : p
    ))
  }

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="text-center text-gray-600">Loading projects...</div>
      </div>
    )
  }

  const activeProjects = projects.filter(p => p.status === 'active').length
  const totalProjects = projects.length

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex justify-between items-center mb-6">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">Kubernetes Projects</h2>
            <p className="text-sm text-gray-600 mt-1">
              {totalProjects} total • {activeProjects} active • Namespace: user-{userId}
            </p>
          </div>
          <button
            onClick={() => setShowCreateForm(!showCreateForm)}
            className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 transition-colors font-medium"
          >
            {showCreateForm ? 'Cancel' : 'Create Project'}
          </button>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-md p-4 mb-6">
            <div className="text-red-800">
              <strong>Error:</strong> {error}
            </div>
            <button 
              onClick={fetchProjects}
              className="mt-2 text-blue-600 hover:text-blue-700 underline text-sm"
            >
              Retry
            </button>
          </div>
        )}

        {showCreateForm && (
          <div className="mb-6">
            <CreateProjectForm
              userId={userId}
              onProjectCreated={handleProjectCreated}
              onCancel={() => setShowCreateForm(false)}
            />
          </div>
        )}

        {projects.length === 0 ? (
          <div className="text-center py-12">
            <div className="text-gray-400 mb-4">
              <svg className="mx-auto h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} 
                      d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h.01M17 7h.01" />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">No projects yet</h3>
            <p className="text-gray-500 mb-4">
              Create your first project to deploy a Goose API instance to Kubernetes
            </p>
            <button
              onClick={() => setShowCreateForm(true)}
              className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 transition-colors font-medium"
            >
              Create Your First Project
            </button>
          </div>
        ) : (
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {projects.map((project) => (
              <ProjectCard
                key={project.project_id}
                project={project}
                userId={userId}
                onProjectDeleted={handleProjectDeleted}
                onProjectUpdated={handleProjectUpdated}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
