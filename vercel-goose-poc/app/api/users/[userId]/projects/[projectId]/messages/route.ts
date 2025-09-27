import { NextRequest, NextResponse } from 'next/server'
import { connectDB } from '@/lib/db'
import { Project } from '@/lib/models'

// POST /api/users/[userId]/projects/[projectId]/messages - Send message to Goose API in K8s
export async function POST(
  request: NextRequest,
  { params }: { params: { userId: string; projectId: string } }
) {
  try {
    await connectDB()
    
    const project = await Project.findOne({
      user_id: params.userId,
      project_id: params.projectId,
      status: 'active'
    })
    
    if (!project || !project.endpoint) {
      return NextResponse.json(
        { error: 'Project not active or endpoint not available' },
        { status: 404 }
      )
    }
    
    const body = await request.json()
    const { message, sessionId } = body
    
    if (!message) {
      return NextResponse.json(
        { error: 'Message is required' },
        { status: 400 }
      )
    }
    
    // For POC, we'll use a default session or create one
    const targetSessionId = sessionId || 'poc-session-1'
    
    // Proxy request to Goose API in Kubernetes pod
    const gooseApiUrl = `${project.endpoint}/api/v1/sessions/${targetSessionId}/messages`
    
    try {
      const gooseResponse = await fetch(gooseApiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message })
      })
      
      if (!gooseResponse.ok) {
        throw new Error(`Goose API error: ${gooseResponse.status} ${gooseResponse.statusText}`)
      }
      
      // For POC, we'll just return the response directly
      // In production, this would stream SSE
      const responseData = await gooseResponse.json()
      
      return NextResponse.json({
        id: Date.now().toString(),
        message,
        response: responseData.response || responseData.content || 'Response received from Goose API',
        timestamp: new Date().toISOString(),
        session_id: targetSessionId,
        k8s_info: {
          namespace: project.namespace,
          deployment: project.deployment,
          endpoint: project.endpoint
        }
      })
      
    } catch (fetchError) {
      console.error('Error calling Goose API:', fetchError)
      
      // For POC, provide a fallback response if Goose API is not responding
      return NextResponse.json({
        id: Date.now().toString(),
        message,
        response: `[POC Response] I received your message: "${message}". The Kubernetes pod at ${project.endpoint} is running! (Note: Actual Goose API may not be responding yet)`,
        timestamp: new Date().toISOString(),
        session_id: targetSessionId,
        k8s_info: {
          namespace: project.namespace,
          deployment: project.deployment,
          endpoint: project.endpoint,
          warning: 'Using fallback response - check if Goose API is properly deployed'
        }
      })
    }
    
  } catch (error) {
    console.error('Error processing message:', error)
    return NextResponse.json(
      { error: 'Failed to process message' },
      { status: 500 }
    )
  }
}
