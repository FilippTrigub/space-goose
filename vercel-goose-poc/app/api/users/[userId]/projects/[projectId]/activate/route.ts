import { NextRequest, NextResponse } from 'next/server'
import { ProjectService } from '@/lib/project-service'

// POST /api/users/[userId]/projects/[projectId]/activate - Activate project in K8s
export async function POST(
  request: NextRequest,
  { params }: { params: { userId: string; projectId: string } }
) {
  try {
    const projectService = new ProjectService()
    const result = await projectService.activateProject(params.userId, params.projectId)
    
    return NextResponse.json({
      success: true,
      project: result.project,
      logs: result.logs,
      endpoint: result.project.endpoint
    })
    
  } catch (error) {
    console.error('Error activating project:', error)
    
    return NextResponse.json(
      { 
        error: 'Failed to activate project',
        details: error instanceof Error ? error.message : 'Unknown error'
      },
      { status: 500 }
    )
  }
}
