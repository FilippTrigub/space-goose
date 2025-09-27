import { NextRequest, NextResponse } from 'next/server'
import { ProjectService } from '@/lib/project-service'

// GET /api/users/[userId]/projects - List user's projects
export async function GET(request: NextRequest, { params }: { params: { userId: string } }) {
  try {
    const projectService = new ProjectService()
    const projects = await projectService.getProjects(params.userId)
    
    return NextResponse.json({ projects })
  } catch (error) {
    console.error('Error fetching projects:', error)
    return NextResponse.json(
      { error: 'Failed to fetch projects' },
      { status: 500 }
    )
  }
}

// POST /api/users/[userId]/projects - Create new project
export async function POST(request: NextRequest, { params }: { params: { userId: string } }) {
  try {
    const body = await request.json()
    const { name, description = '' } = body
    
    if (!name) {
      return NextResponse.json(
        { error: 'Project name is required' },
        { status: 400 }
      )
    }
    
    const projectService = new ProjectService()
    const project = await projectService.createProject(params.userId, name, description)
    
    return NextResponse.json({ project }, { status: 201 })
  } catch (error) {
    console.error('Error creating project:', error)
    
    if (error instanceof Error && error.message.includes('duplicate')) {
      return NextResponse.json(
        { error: 'Project with this name already exists' },
        { status: 409 }
      )
    }
    
    return NextResponse.json(
      { error: 'Failed to create project' },
      { status: 500 }
    )
  }
}
