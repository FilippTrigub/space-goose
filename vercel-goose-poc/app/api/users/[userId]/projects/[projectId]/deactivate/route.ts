import { NextRequest, NextResponse } from 'next/server'
import { ProjectService } from '@/lib/project-service'

// POST /api/users/[userId]/projects/[projectId]/deactivate - Deactivate project in K8s
export async function POST(
  request: NextRequest,
  { params }: { params: { userId: string; projectId: string } }
) {
  try {
    const projectService = new ProjectService()
    const result = await projectService.deactivateProject(params.userId, params.projectId)
    
    return NextResponse.json({
      success: true,
      project: result.project,
      logs: result.logs
    })
    
  } catch (error) {
    console.error('Error deactivating project:', error)
    
    return NextResponse.json(
      { 
        error: 'Failed to deactivate project',
        details: error instanceof Error ? error.message : 'Unknown error'
      },
      { status: 500 }
    )
  }
}
