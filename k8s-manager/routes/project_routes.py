from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from typing import List
import json
import httpx
import asyncio
from datetime import datetime

from models import ProjectCreate, ProjectUpdate, Project, User, MessageRequest, SessionCreate, Session, ProjectUpdateGitHubKey
from services import mongodb_service, k8s_service

router = APIRouter()

# Static user list for MVP
users = [{"id": "user1", "name": "User 1"}, {"id": "user2", "name": "User 2"}]

@router.get("/users", response_model=List[User])
async def get_users():
    return [User(**user) for user in users]

@router.get("/users/{user_id}/projects")
async def get_projects(user_id: str):
    projects = mongodb_service.list_projects(user_id)
    return [{
        "id": str(project["_id"]),
        "user_id": project["user_id"],
        "name": project["name"],
        "status": project["status"],
        "endpoint": project.get("endpoint"),
        "github_key_set": project.get("github_key_set", False),
        "sessions": project.get("sessions", []),
        "created_at": project.get("created_at"),
        "updated_at": project.get("updated_at")
    } for project in projects]

@router.post("/users/{user_id}/projects")
async def create_project(user_id: str, project: ProjectCreate):
    project_data = {
        "user_id": user_id,
        "name": project.name,
        "status": "inactive",
        "sessions": [],
        "github_key_set": bool(project.github_key),
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    result = mongodb_service.create_project(project_data)
    project_id = str(result.inserted_id)
    
    # Create K8s resources but don't activate yet
    try:
        k8s_service.apply_project_resources(user_id, project_id, project.github_key)
        
        # Store GitHub key in MongoDB if provided (masked)
        if project.github_key:
            mongodb_service.store_github_key(project_id, project.github_key)
            
    except Exception as e:
        # Rollback MongoDB record if K8s fails
        mongodb_service.delete_project(project_id)
        raise HTTPException(status_code=500, detail=f"Failed to create K8s resources: {str(e)}")
    
    return {"message": "Project created successfully", "project_id": project_id}

@router.put("/users/{user_id}/projects/{project_id}")
async def update_project(user_id: str, project_id: str, project: ProjectUpdate):
    update_data = {
        "name": project.name,
        "updated_at": datetime.utcnow()
    }
    result = mongodb_service.update_project(project_id, update_data)
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"message": "Project updated successfully"}

@router.delete("/users/{user_id}/projects/{project_id}")
async def delete_project(user_id: str, project_id: str):
    # First deactivate if active
    project = mongodb_service.get_project(project_id)
    if project and project["status"] == "active":
        k8s_service.scale_project(user_id, project_id, 0)
    
    # Delete K8s resources
    k8s_service.delete_project_resources(user_id, project_id)
    
    # Delete from MongoDB
    result = mongodb_service.delete_project(project_id)
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return {"message": "Project deleted successfully"}

@router.post("/users/{user_id}/projects/{project_id}/activate")
async def activate_project(user_id: str, project_id: str):
    try:
        # Scale up deployment
        k8s_service.scale_project(user_id, project_id, 1)
        
        # Wait for pod to be ready - simple approach for POC
        await asyncio.sleep(15)
        
        # Get LoadBalancer IP/hostname
        try:
            endpoint = k8s_service.get_project_endpoint(user_id, project_id)
        except Exception as e:
            # If LoadBalancer IP is not ready, scale back down and fail
            k8s_service.scale_project(user_id, project_id, 0)
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to get project endpoint: {str(e)}. LoadBalancer IP may not be ready yet."
            )
        
        # Update status in MongoDB
        mongodb_service.update_project_status(project_id, "active", endpoint)
        
        return {"message": "Project activated successfully", "endpoint": endpoint}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to activate project: {str(e)}")

@router.put("/users/{user_id}/projects/{project_id}/github-key")
async def update_project_github_key(user_id: str, project_id: str, github_key_data: ProjectUpdateGitHubKey):
    """Update GitHub key for an existing project"""
    # Check if project exists
    project = mongodb_service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if project["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Project belongs to different user")
    
    try:
        # Update Kubernetes secret
        k8s_service.update_github_secret(user_id, project_id, github_key_data.github_key)
        
        # Update MongoDB record
        mongodb_service.update_github_key(project_id, github_key_data.github_key)
        
        action = "updated" if github_key_data.github_key else "removed"
        return {"message": f"GitHub key {action} successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update GitHub key: {str(e)}")

@router.post("/users/{user_id}/projects/{project_id}/deactivate")
async def deactivate_project(user_id: str, project_id: str):
    try:
        # Scale down deployment
        k8s_service.scale_project(user_id, project_id, 0)
        
        # Update status in MongoDB
        mongodb_service.update_project_status(project_id, "inactive")
        
        return {"message": "Project deactivated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to deactivate project: {str(e)}")

# Session Management Endpoints

@router.post("/users/{user_id}/projects/{project_id}/sessions")
async def create_session(user_id: str, project_id: str, session: SessionCreate):
    """Create a new session in the Goose API and store it in the project"""
    # Check if project exists and is active
    project = mongodb_service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if project["status"] != "active":
        raise HTTPException(status_code=400, detail="Project must be active to create sessions")
    
    endpoint = k8s_service.get_project_endpoint(user_id, project_id)
    if not endpoint:
        raise HTTPException(status_code=500, detail="Project endpoint not available")
    
    try:
        # Create session in Goose API
        create_url = f"http://{endpoint}/api/v1/sessions"
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(create_url)

            if response.status_code != 201:
                raise HTTPException(status_code=500, detail=f"Failed to create session in Goose API: {response.status_code}")
            
            session_data = response.json()
            session_id = session_data["session_id"]
        
        # Store session in project
        session_record = {
            "session_id": session_id,
            "name": session.name or f"Session {len(project.get('sessions', [])) + 1}",
            "created_at": datetime.utcnow(),
            "message_count": 0
        }
        
        mongodb_service.add_session_to_project(project_id, session_record)
        
        return {"message": "Session created successfully", "session": session_record}
        
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"Failed to connect to Goose API: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create session: {str(e)}")

@router.get("/users/{user_id}/projects/{project_id}/sessions")
async def get_project_sessions(user_id: str, project_id: str):
    """Get all sessions for a project"""
    project = mongodb_service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return {"sessions": project.get("sessions", [])}

@router.delete("/users/{user_id}/projects/{project_id}/sessions/{session_id}")
async def delete_session(user_id: str, project_id: str, session_id: str):
    """Delete a session from both Goose API and project data"""
    project = mongodb_service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Try to delete from Goose API if project is active
    if project["status"] == "active" and project.get("endpoint"):
        try:
            delete_url = f"http://{project['endpoint']}/api/v1/sessions/{session_id}"
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.delete(delete_url)
        except:
            # Continue even if Goose API deletion fails
            pass
    
    # Remove from project data
    result = mongodb_service.remove_session_from_project(project_id, session_id)
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Session not found in project")
    
    return {"message": "Session deleted successfully"}

@router.post("/users/{user_id}/projects/{project_id}/messages")
async def proxy_message(user_id: str, project_id: str, message: MessageRequest):
    """Send message to a specific session and stream the response"""
    # Get project to check if active
    project = mongodb_service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if project["status"] != "active":
        raise HTTPException(status_code=400, detail="Project is not active")
    
    endpoint = k8s_service.get_project_endpoint(user_id, project_id)
    if not endpoint:
        raise HTTPException(status_code=500, detail="Project endpoint not available")
    
    # Verify session exists in project
    sessions = project.get("sessions", [])
    session_exists = any(s["session_id"] == message.session_id for s in sessions)
    if not session_exists:
        raise HTTPException(status_code=404, detail="Session not found in project")
    
    try:
        # Forward to Goose API
        goose_url = f"http://{endpoint}/api/v1/sessions/{message.session_id}/messages"
        print(f"Proxying message to: {goose_url}")
        
        async def stream_response():
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream(
                    "POST",
                    goose_url,
                    json={"message": message.content},  # Note: API expects "message" not "content"
                    headers={"Accept": "text/event-stream"}
                ) as response:
                    if response.status_code != 200:
                        error_text = await response.aread()
                        yield f"data: {{\"error\": \"Goose API returned {response.status_code}: {error_text.decode()}\"}}\n\n"
                        return
                    
                    # Stream the Server-Sent Events
                    async for chunk in response.aiter_text():
                        # Parse each SSE chunk and extract the JSON content
                        lines = chunk.strip().split('\n')
                        for line in lines:
                            if line.startswith('data: '):
                                try:
                                    # Extract JSON from SSE data line
                                    json_str = line[6:]  # Remove 'data: ' prefix
                                    if json_str.strip():  # Skip empty data lines
                                        # Parse and re-emit the JSON
                                        parsed_data = json.loads(json_str)
                                        yield f"data: {json.dumps(parsed_data)}\n\n"
                                except json.JSONDecodeError:
                                    # If not valid JSON, pass through as-is
                                    yield f"data: {{\"raw\": {json.dumps(json_str)}}}\n\n"
                            elif line == '':
                                # Empty line - keep for SSE format
                                yield '\n'
                            else:
                                # Other SSE lines (like event:, id:, etc.)
                                yield f"{line}\n"
        
        return StreamingResponse(
            stream_response(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
        )
    
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"Failed to connect to Goose API: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to proxy message: {str(e)}")
