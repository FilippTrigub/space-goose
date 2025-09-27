'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { IProject } from '@/lib/models'

interface ChatMessage {
  id: string
  message: string
  response: string
  timestamp: string
  session_id?: string
  k8s_info?: any
}

export default function ChatPage() {
  const params = useParams()
  const router = useRouter()
  const userId = params.userId as string
  const projectId = params.projectId as string
  
  const [project, setProject] = useState<IProject | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [currentMessage, setCurrentMessage] = useState('')
  const [sending, setSending] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    fetchProject()
  }, [userId, projectId])

  const fetchProject = async () => {
    try {
      const response = await fetch(`/api/users/${userId}/projects`)
      if (!response.ok) throw new Error('Failed to fetch projects')
      const data = await response.json()
      const foundProject = data.projects.find((p: IProject) => p.project_id === projectId)
      
      if (!foundProject) {
        throw new Error('Project not found')
      }
      
      if (foundProject.status !== 'active') {
        setError(`Project is ${foundProject.status}. Please activate it first.`)
      }
      
      setProject(foundProject)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load project')
    } finally {
      setLoading(false)
    }
  }

  const sendMessage = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!currentMessage.trim() || sending) {
      return
    }

    const messageText = currentMessage.trim()
    setCurrentMessage('')
    setSending(true)

    try {
      const response = await fetch(`/api/users/${userId}/projects/${projectId}/messages`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          message: messageText,
          sessionId: 'poc-session-1' // Fixed for POC
        })
      })
      
      const data = await response.json()
      
      if (!response.ok) {
        throw new Error(data.error || 'Failed to send message')
      }
      
      const newMessage: ChatMessage = {
        id: data.id || Date.now().toString(),
        message: messageText,
        response: data.response || 'No response received',
        timestamp: data.timestamp || new Date().toISOString(),
        session_id: data.session_id,
        k8s_info: data.k8s_info
      }
      
      setMessages(prev => [...prev, newMessage])
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send message')
    } finally {
      setSending(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 py-8">
        <div className="container mx-auto px-4 max-w-4xl">
          <div className="bg-white rounded-lg shadow p-8">
            <div className="text-center text-gray-600">Loading project...</div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="container mx-auto px-4 max-w-4xl">
        <div className="bg-white rounded-lg shadow overflow-hidden">
          {/* Header */}
          <div className="border-b border-gray-200 p-6 bg-gray-50">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-2xl font-bold text-gray-900">
                  Chat: {project?.name || 'Project'}
                </h1>
                {project && (
                  <div className="mt-2 space-y-1">
                    <div className="text-sm text-gray-600">
                      <span className="font-medium">Status:</span>
                      <span className={`ml-2 px-2 py-1 rounded text-xs font-medium ${
                        project.status === 'active' 
                          ? 'bg-green-100 text-green-800' 
                          : 'bg-red-100 text-red-800'
                      }`}>
                        {project.status}
                      </span>
                    </div>
                    <div className="text-sm text-gray-600">
                      <span className="font-medium">Namespace:</span>
                      <span className="ml-2 font-mono text-xs">{project.namespace}</span>
                    </div>
                    {project.endpoint && (
                      <div className="text-sm text-gray-600">
                        <span className="font-medium">K8s Endpoint:</span>
                        <a href={project.endpoint} target="_blank" rel="noopener noreferrer" 
                           className="ml-2 font-mono text-xs text-blue-600 hover:text-blue-800 underline">
                          {project.endpoint}
                        </a>
                      </div>
                    )}
                  </div>
                )}
              </div>
              <button
                onClick={() => router.back()}
                className="bg-gray-600 text-white px-4 py-2 rounded-md hover:bg-gray-700 transition-colors"
              >
                ← Back to Projects
              </button>
            </div>
          </div>

          {/* Error Display */}
          {error && (
            <div className="border-b border-gray-200 p-4 bg-red-50">
              <div className="text-red-800">
                <strong>Error:</strong> {error}
              </div>
              {project?.status !== 'active' && (
                <div className="mt-3 space-x-2">
                  <button
                    onClick={() => router.back()}
                    className="text-blue-600 hover:text-blue-700 underline text-sm"
                  >
                    Go back to activate project
                  </button>
                  <button
                    onClick={fetchProject}
                    className="text-green-600 hover:text-green-700 underline text-sm"
                  >
                    Refresh status
                  </button>
                </div>
              )}
            </div>
          )}

          {/* Chat Messages */}
          <div className="p-6 min-h-[400px] max-h-[500px] overflow-y-auto bg-gray-50">
            {messages.length === 0 ? (
              <div className="text-center text-gray-500 py-12">
                <div className="bg-white rounded-lg p-8 border border-dashed border-gray-300">
                  <div className="text-gray-400 mb-4">
                    <svg className="mx-auto h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} 
                            d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                    </svg>
                  </div>
                  <h3 className="text-lg font-medium text-gray-900 mb-2">Start chatting with Goose</h3>
                  <p className="text-gray-500">
                    Send a message to interact with the Goose API running in your Kubernetes pod
                  </p>
                </div>
              </div>
            ) : (
              <div className="space-y-6">
                {messages.map((msg) => (
                  <div key={msg.id} className="space-y-3">
                    {/* User Message */}
                    <div className="flex justify-end">
                      <div className="bg-blue-600 text-white rounded-lg px-4 py-3 max-w-md shadow-sm">
                        <p className="text-sm">{msg.message}</p>
                        <p className="text-xs opacity-75 mt-2">
                          {new Date(msg.timestamp).toLocaleTimeString()}
                        </p>
                      </div>
                    </div>
                    
                    {/* Goose Response */}
                    <div className="flex justify-start">
                      <div className="bg-white border border-gray-200 rounded-lg px-4 py-3 max-w-md shadow-sm">
                        <div className="flex items-start space-x-2">
                          <div className="bg-green-100 text-green-800 px-2 py-1 rounded text-xs font-medium">
                            Goose
                          </div>
                          <div className="flex-1">
                            <p className="text-sm text-gray-900">{msg.response}</p>
                            <div className="mt-2 text-xs text-gray-500">
                              <div>{new Date(msg.timestamp).toLocaleString()}</div>
                              {msg.session_id && (
                                <div className="mt-1">Session: {msg.session_id}</div>
                              )}
                              {msg.k8s_info?.warning && (
                                <div className="mt-1 text-yellow-600 font-medium">
                                  ⚠️ {msg.k8s_info.warning}
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Message Input */}
          <div className="border-t border-gray-200 p-6 bg-white">
            {project?.status === 'active' ? (
              <form onSubmit={sendMessage} className="space-y-4">
                <div className="flex gap-3">
                  <input
                    type="text"
                    value={currentMessage}
                    onChange={(e) => setCurrentMessage(e.target.value)}
                    placeholder="Ask Goose anything..."
                    disabled={sending}
                    className="flex-1 px-4 py-3 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:opacity-50"
                  />
                  <button
                    type="submit"
                    disabled={sending || !currentMessage.trim()}
                    className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
                  >
                    {sending ? 'Sending...' : 'Send'}
                  </button>
                </div>
                <div className="text-xs text-gray-500">
                  💡 Messages are sent to the Goose API running in Kubernetes pod: {project.deployment}
                </div>
              </form>
            ) : (
              <div className="text-center py-8">
                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                  <div className="text-yellow-800">
                    <strong>Project not active</strong>
                  </div>
                  <p className="text-yellow-700 text-sm mt-1">
                    Current status: {project?.status || 'unknown'}
                  </p>
                  <div className="mt-4">
                    <button
                      onClick={() => router.back()}
                      className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 transition-colors"
                    >
                      Go back to activate
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
