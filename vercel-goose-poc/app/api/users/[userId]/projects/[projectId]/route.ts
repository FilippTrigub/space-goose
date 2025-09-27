import { NextRequest, NextResponse } from 'next/server'
import { ProjectService } from '@/lib/project-service'

// DELETE /api/users/[userId]/projects/[projectId] - Delete project
export async function DELETE(
  request: NextRequest,
  { params }: { params: { userId: string; projectId: string } }
) {
  try {
    const projectService = new ProjectService()
    await projectService.deleteProject(params.userId, params.projectId)
    
    return NextResponse.json({ success: true })
  } catch (error) {
    console.error('Error deleting project:', error)
    
    if (error instanceof Error && error.message === 'Project not found') {
      return NextResponse.json(
        { error: 'Project not found' },
        { status: 404 }
      )
    }
    
    return NextResponse.json(
      { error: 'Failed to delete project' },
      { status: 500 }
    )
  }
}
