from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from typing import List
import json
import httpx
import asyncio
from datetime import datetime

from models import (
    ProjectCreate,
    ProjectUpdate,
    Project,
    User,
    MessageRequest,
    SessionCreate,
    Session,
    ProjectUpdateGitHubKey,
    Extension,
    ExtensionCreate,
    ExtensionToggle,
    SettingUpdate,
    UserGitHubKey,
)
from services import mongodb_service, k8s_service

router = APIRouter()

# Static user list for MVP
users = [{"id": "user1", "name": "User 1"}, {"id": "user2", "name": "User 2"}]


@router.get("/users", response_model=List[User])
async def get_users():
    """
    Get a list of all available users.

    Returns:
        List[User]: A list of User objects containing user IDs and names

    Example:
        Returns static user list for MVP version
    """
    return [User(**user) for user in users]


@router.get("/users/{user_id}/projects", operation_id="get_user_projects")
async def get_projects(user_id: str):
    """
    Get all projects for a specific user.

    Args:
        user_id (str): The ID of the user to fetch projects for

    Returns:
        List[dict]: A list of project dictionaries containing project details
            - id: Project identifier
            - user_id: Owner of the project
            - name: Project name
            - status: Current status (active/inactive)
            - endpoint: URL endpoint when active
            - github_key_set: Whether GitHub key is configured
            - sessions: List of associated sessions
            - created_at: Creation timestamp
            - updated_at: Last update timestamp

    Raises:
        HTTPException: Not explicitly raised but could be from the database service

    Example:
        Retrieves all projects from MongoDB for the specified user
    """
    projects = mongodb_service.list_projects(user_id)
    return [
        {
            "id": str(project["_id"]),
            "user_id": project["user_id"],
            "name": project["name"],
            "status": project["status"],
            "endpoint": project.get("endpoint"),
            "github_key_set": project.get("github_key_set", False),
            "sessions": project.get("sessions", []),
            "created_at": project.get("created_at"),
            "updated_at": project.get("updated_at"),
        }
        for project in projects
    ]


@router.post("/users/{user_id}/projects", operation_id="create_project")
async def create_project(user_id: str, project: ProjectCreate):
    """
    Create a new project with Kubernetes resources.

    Args:
        user_id (str): The ID of the user who owns the project
        project (ProjectCreate): Project creation data containing:
            - name: Name for the new project
            - github_key (optional): GitHub API key for repository access

    Returns:
        dict: Response containing project creation confirmation
            - message: Success message
            - project_id: ID of the newly created project

    Raises:
        HTTPException: When Kubernetes resource creation fails
            - 500: Failed to create K8s resources with error details

    Example:
        Creates a project record in MongoDB and corresponding K8s resources
        If GitHub key is provided, it's stored securely for the project
    """
    project_data = {
        "user_id": user_id,
        "name": project.name,
        "status": "inactive",
        "sessions": [],
        "github_key_set": bool(project.github_key),
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    result = mongodb_service.create_project(project_data)
    project_id = str(result.inserted_id)

    # If no project GitHub key is provided, check if user has a global key
    github_key = project.github_key
    if not github_key and mongodb_service.has_user_github_key(user_id):
        # User has a global key, update project to show it's using a key
        project_data["github_key_set"] = True
        project_data["github_key_source"] = "user"
        mongodb_service.update_project(
            project_id, {"$set": {"github_key_set": True, "github_key_source": "user"}}
        )
        # Get the global key from Kubernetes
        user_secret_exists = k8s_service.get_user_github_secret(user_id)
        if user_secret_exists:
            # Use the user's global key but don't store it in the project
            print(f"Using global GitHub key for project {project_id}")

    # Create K8s resources but don't activate yet
    try:
        k8s_service.apply_project_resources(user_id, project_id, github_key)

        # Wait for pod to be ready - simple approach for POC
        await asyncio.sleep(60)

        # Get LoadBalancer IP/hostname
        try:
            endpoint = k8s_service.get_project_endpoint(user_id, project_id)
        except Exception as e:
            # If LoadBalancer IP is not ready, scale back down and fail
            k8s_service.scale_project(user_id, project_id, 0)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get project endpoint: {str(e)}. LoadBalancer IP may not be ready yet.",
            )

        # Update status in MongoDB
        mongodb_service.update_project_status(project_id, "active", endpoint)

        # Store GitHub key in MongoDB if provided (masked)
        if github_key:
            mongodb_service.store_github_key(project_id, github_key)

    except Exception as e:
        # Rollback MongoDB record if K8s fails
        mongodb_service.delete_project(project_id)
        raise HTTPException(
            status_code=500, detail=f"Failed to create K8s resources: {str(e)}"
        )

    return {"message": "Project created successfully", "project_id": project_id}


@router.put("/users/{user_id}/projects/{project_id}", operation_id="update_project")
async def update_project(user_id: str, project_id: str, project: ProjectUpdate):
    """
    Update an existing project's name and metadata.

    Args:
        user_id (str): The ID of the user who owns the project
        project_id (str): The ID of the project to update
        project (ProjectUpdate): Project update data containing:
            - name: New name for the project

    Returns:
        dict: Response containing update confirmation
            - message: Success message

    Raises:
        HTTPException: When project is not found
            - 404: Project not found if no matching project exists

    Example:
        Updates project name and updates the last modified timestamp
    """
    update_data = {"name": project.name, "updated_at": datetime.utcnow()}
    result = mongodb_service.update_project(project_id, {"$set": update_data})
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"message": "Project updated successfully"}


@router.delete("/users/{user_id}/projects/{project_id}", operation_id="delete_project")
async def delete_project(user_id: str, project_id: str):
    """
    Delete a project and all its associated Kubernetes resources.

    Args:
        user_id (str): The ID of the user who owns the project
        project_id (str): The ID of the project to delete

    Returns:
        dict: Response containing deletion confirmation
            - message: Success message

    Raises:
        HTTPException: When project is not found
            - 404: Project not found if no matching project exists

    Example:
        First deactivates the project if active, removes all K8s resources,
        then deletes the project record from MongoDB
    """
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


@router.post(
    "/users/{user_id}/projects/{project_id}/activate", operation_id="activate_project"
)
async def activate_project(user_id: str, project_id: str):
    """
    Activate a project by scaling up its deployment and retrieving the endpoint.

    Args:
        user_id (str): The ID of the user who owns the project
        project_id (str): The ID of the project to activate

    Returns:
        dict: Response containing activation confirmation
            - message: Success message
            - endpoint: The generated endpoint URL for accessing the project

    Raises:
        HTTPException: When activation fails
            - 500: Failed to activate project with error details
            - 500: Failed to get project endpoint if LoadBalancer IP is not ready

    Example:
        Scales up the K8s deployment to 1 replica, waits for the pod to be ready,
        retrieves the LoadBalancer IP/hostname, and updates project status in MongoDB
    """
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
                detail=f"Failed to get project endpoint: {str(e)}. LoadBalancer IP may not be ready yet.",
            )

        # Update status in MongoDB
        mongodb_service.update_project_status(project_id, "active", endpoint)

        return {"message": "Project activated successfully", "endpoint": endpoint}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to activate project: {str(e)}"
        )


@router.put(
    "/users/{user_id}/projects/{project_id}/github-key",
    operation_id="update_project_github_key",
)
async def update_project_github_key(
    user_id: str, project_id: str, github_key_data: ProjectUpdateGitHubKey
):
    """Update GitHub key for an existing project"""
    # Check if project exists
    project = mongodb_service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Project belongs to different user")

    try:
        # Update Kubernetes secret
        k8s_service.update_github_secret(
            user_id, project_id, github_key_data.github_key
        )

        # Update MongoDB record
        mongodb_service.update_github_key(project_id, github_key_data.github_key)

        # Update the source to "project" since it's explicitly set for this project
        if github_key_data.github_key:
            mongodb_service.update_project(
                project_id, {"$set": {"github_key_source": "project"}}
            )
        else:
            # If removing project key, check if user has global key to fall back to
            if mongodb_service.has_user_github_key(user_id):
                mongodb_service.update_project(
                    project_id,
                    {"$set": {"github_key_source": "user", "github_key_set": True}},
                )
            else:
                mongodb_service.update_project(
                    project_id,
                    {
                        "$set": {"github_key_set": False},
                        "$unset": {"github_key_source": ""},
                    },
                )

        action = "updated" if github_key_data.github_key else "removed"
        return {"message": f"GitHub key {action} successfully"}

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to update GitHub key: {str(e)}"
        )


@router.post(
    "/users/{user_id}/projects/{project_id}/deactivate",
    operation_id="deactivate_project",
)
async def deactivate_project(user_id: str, project_id: str):
    """
    Deactivate a project by scaling down its deployment.

    Args:
        user_id (str): The ID of the user who owns the project
        project_id (str): The ID of the project to deactivate

    Returns:
        dict: Response containing deactivation confirmation
            - message: Success message

    Raises:
        HTTPException: When deactivation fails
            - 500: Failed to deactivate project with error details

    Example:
        Scales down the K8s deployment to 0 replicas and updates project status in MongoDB
    """
    try:
        # Scale down deployment
        k8s_service.scale_project(user_id, project_id, 0)

        # Update status in MongoDB
        mongodb_service.update_project_status(project_id, "inactive")

        return {"message": "Project deactivated successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to deactivate project: {str(e)}"
        )


# New user GitHub token endpoints
@router.put("/users/{user_id}/github-key", operation_id="update_user_github_key")
async def update_user_github_key(user_id: str, github_key_data: UserGitHubKey):
    """Set or update the global GitHub key for a user"""
    try:
        # First store in K8s as secret
        if github_key_data.github_key:
            k8s_service.create_or_update_user_github_secret(
                user_id, github_key_data.github_key
            )

            # Then store in MongoDB (masked)
            mongodb_service.store_user_github_key(user_id, github_key_data.github_key)

            # Update any projects that don't have their own key to use this one
            projects = mongodb_service.list_projects(user_id)
            for project in projects:
                project_id = str(project["_id"])
                # Skip projects that have their own key
                if project.get("github_key_source") != "project" and not project.get(
                    "github_key_masked"
                ):
                    mongodb_service.update_project(
                        project_id,
                        {"$set": {"github_key_set": True, "github_key_source": "user"}},
                    )

            return {"message": "Global GitHub key set successfully"}
        else:
            # Remove the key from K8s
            k8s_service.delete_user_github_secret(user_id)

            # Remove from MongoDB
            mongodb_service.delete_user_github_key(user_id)

            # Update projects that were using the global key
            projects = mongodb_service.list_projects(user_id)
            for project in projects:
                project_id = str(project["_id"])
                # Only update projects that were using the global key
                if project.get("github_key_source") == "user":
                    mongodb_service.update_project(
                        project_id,
                        {
                            "$set": {"github_key_set": False},
                            "$unset": {"github_key_source": ""},
                        },
                    )

            return {"message": "Global GitHub key removed successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to update global GitHub key: {str(e)}"
        )


@router.get("/users/{user_id}/github-key", operation_id="check_user_github_key")
async def check_user_github_key(user_id: str):
    """Check if a user has a global GitHub key set"""
    try:
        # Check MongoDB for user
        has_key = mongodb_service.has_user_github_key(user_id)
        return {"github_key_set": has_key}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to check global GitHub key: {str(e)}"
        )


@router.delete("/users/{user_id}/github-key", operation_id="delete_user_github_key")
async def delete_user_github_key(user_id: str):
    """Remove the global GitHub key for a user"""
    try:
        # Remove from K8s
        k8s_service.delete_user_github_secret(user_id)

        # Remove from MongoDB
        mongodb_service.delete_user_github_key(user_id)

        # Update projects that were using the global key
        projects = mongodb_service.list_projects(user_id)
        for project in projects:
            project_id = str(project["_id"])
            # Only update projects that were using the global key
            if project.get("github_key_source") == "user":
                mongodb_service.update_project(
                    project_id,
                    {
                        "$set": {"github_key_set": False},
                        "$unset": {"github_key_source": ""},
                    },
                )

        return {"message": "Global GitHub key removed successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to delete global GitHub key: {str(e)}"
        )


# Session Management Endpoints


@router.post(
    "/users/{user_id}/projects/{project_id}/sessions", operation_id="create_session"
)
async def create_session(user_id: str, project_id: str, session: SessionCreate):
    """Create a new session in the Goose API and store it in the project"""
    # Check if project exists and is active
    project = mongodb_service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project["status"] != "active":
        raise HTTPException(
            status_code=400, detail="Project must be active to create sessions"
        )

    endpoint = k8s_service.get_project_endpoint(user_id, project_id)
    if not endpoint:
        raise HTTPException(status_code=500, detail="Project endpoint not available")

    try:
        # Create session in Goose API
        create_url = f"http://{endpoint}/api/v1/sessions"
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(create_url)

            if response.status_code != 201:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to create session in Goose API: {response.status_code}",
                )

            session_data = response.json()
            session_id = session_data["session_id"]

        # Store session in project
        session_record = {
            "session_id": session_id,
            "name": session.name or f"Session {len(project.get('sessions', [])) + 1}",
            "created_at": datetime.utcnow(),
            "message_count": 0,
        }

        mongodb_service.add_session_to_project(project_id, session_record)

        return {"message": "Session created successfully", "session": session_record}

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to connect to Goose API: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to create session: {str(e)}"
        )


@router.get(
    "/users/{user_id}/projects/{project_id}/sessions",
    operation_id="get_all_project_sessions",
)
async def get_project_sessions(user_id: str, project_id: str):
    """Get all sessions for a project"""
    print(f"getting session with user {user_id} and project {project_id}")
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


@router.get(
    "/users/{user_id}/projects/{project_id}/sessions/{session_id}/messages",
    operation_id="get_session_messages",
)
async def get_session_messages(user_id: str, project_id: str, session_id: str):
    """Get message history for a session"""
    # Check if project exists and user has access
    project = mongodb_service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Project belongs to different user")

    if project["status"] != "active":
        raise HTTPException(status_code=400, detail="Project is not active")

    endpoint = k8s_service.get_project_endpoint(user_id, project_id)
    if not endpoint:
        raise HTTPException(status_code=500, detail="Project endpoint not available")

    # Verify session exists in project
    sessions = project.get("sessions", [])
    session_exists = any(s["session_id"] == session_id for s in sessions)
    if not session_exists:
        raise HTTPException(status_code=404, detail="Session not found in project")

    try:
        # Forward to Goose API to get message history
        goose_url = f"http://{endpoint}/api/v1/sessions/{session_id}/messages"
        print(f"Fetching message history from: {goose_url}")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(goose_url)

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                # Session not found in Goose API, return empty
                return {"session_id": session_id, "messages": [], "total_count": 0}
            else:
                error_text = response.text
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Goose API returned {response.status_code}: {error_text}",
                )

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to connect to Goose API: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch message history: {str(e)}"
        )


# Extension Management Endpoints


@router.get("/users/{user_id}/projects/{project_id}/extensions")
async def get_project_extensions(user_id: str, project_id: str):
    """Get all extensions for a project"""
    project = mongodb_service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Project belongs to different user")

    if project["status"] != "active":
        raise HTTPException(
            status_code=400, detail="Project must be active to manage extensions"
        )

    endpoint = k8s_service.get_project_endpoint(user_id, project_id)
    if not endpoint:
        raise HTTPException(status_code=500, detail="Project endpoint not available")

    try:
        goose_url = f"http://{endpoint}/api/v1/extensions"
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(goose_url)

            if response.status_code == 200:
                return response.json()
            else:
                error_text = response.text
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Goose API returned {response.status_code}: {error_text}",
                )

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to connect to Goose API: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch extensions: {str(e)}"
        )


@router.post("/users/{user_id}/projects/{project_id}/extensions")
async def create_project_extension(
    user_id: str, project_id: str, extension: ExtensionCreate
):
    """Create a new extension for a project"""
    project = mongodb_service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Project belongs to different user")

    if project["status"] != "active":
        raise HTTPException(
            status_code=400, detail="Project must be active to create extensions"
        )

    endpoint = k8s_service.get_project_endpoint(user_id, project_id)
    if not endpoint:
        raise HTTPException(status_code=500, detail="Project endpoint not available")

    try:
        # Prepare extension data for Goose API
        extension_data = {
            "name": extension.name,
            "type": extension.extension_type,  # Use 'type' not 'extension_type'
            "description": extension.description,
        }

        if extension.extension_type == "stdio":
            extension_data["cmd"] = "npx"  # Fixed command
            if extension.args:
                if "-y" not in extension.args:
                    extension.args.insert(0, "-y")
                extension_data["args"] = extension.args
            if extension.envs:
                extension_data["envs"] = extension.envs
        elif extension.extension_type == "streamable_http":
            if not extension.uri:
                raise HTTPException(
                    status_code=400, detail="URI is required for HTTP extensions"
                )
            extension_data["uri"] = extension.uri
            if extension.envs:
                extension_data["envs"] = extension.envs

        # Create extension in Goose API first
        goose_url = f"http://{endpoint}/api/v1/extensions"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(goose_url, json=extension_data)

            if response.status_code != 201:
                error_data = (
                    response.json()
                    if response.headers.get("content-type") == "application/json"
                    else {"detail": response.text}
                )
                raise HTTPException(
                    status_code=response.status_code,
                    detail=error_data.get("message")
                    or error_data.get("detail")
                    or f"Failed to create extension",
                )

        # If extension has environment variables, update K8s deployment
        if extension.envs:
            await update_project_env_vars(user_id, project_id, extension.envs)

        return {
            "message": (
                "Extension created successfully. Pod restarting with new environment variables."
                if extension.envs
                else "Extension created successfully"
            )
        }

    except HTTPException:
        raise
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to connect to Goose API: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to create extension: {str(e)}"
        )


async def update_project_env_vars(user_id: str, project_id: str, env_vars: dict):
    """Update environment variables for a project and restart deployment"""
    try:
        # Update K8s deployment with new environment variables
        k8s_service.update_deployment_env_vars(user_id, project_id, env_vars)

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to update environment variables: {str(e)}"
        )


@router.put("/users/{user_id}/projects/{project_id}/extensions/{extension_name}/toggle")
async def toggle_project_extension(
    user_id: str, project_id: str, extension_name: str, toggle_data: ExtensionToggle
):
    """Toggle extension enabled/disabled for a project"""
    project = mongodb_service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Project belongs to different user")

    if project["status"] != "active":
        raise HTTPException(
            status_code=400, detail="Project must be active to toggle extensions"
        )

    endpoint = k8s_service.get_project_endpoint(user_id, project_id)
    if not endpoint:
        raise HTTPException(status_code=500, detail="Project endpoint not available")

    try:
        goose_url = f"http://{endpoint}/api/v1/extensions/{extension_name}/toggle"
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.put(goose_url, json=toggle_data.dict())

            if response.status_code == 200:
                result = response.json()
                action = "enabled" if toggle_data.enabled else "disabled"
                return {
                    "message": f"Extension {action} successfully",
                    "extension": result,
                }
            else:
                error_data = (
                    response.json()
                    if response.headers.get("content-type") == "application/json"
                    else {"detail": response.text}
                )
                raise HTTPException(
                    status_code=response.status_code,
                    detail=error_data.get("message")
                    or error_data.get("detail")
                    or f"Failed to toggle extension",
                )

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to connect to Goose API: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to toggle extension: {str(e)}"
        )


@router.delete("/users/{user_id}/projects/{project_id}/extensions/{extension_name}")
async def delete_project_extension(user_id: str, project_id: str, extension_name: str):
    """Delete an extension from a project"""
    project = mongodb_service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Project belongs to different user")

    if project["status"] != "active":
        raise HTTPException(
            status_code=400, detail="Project must be active to delete extensions"
        )

    endpoint = k8s_service.get_project_endpoint(user_id, project_id)
    if not endpoint:
        raise HTTPException(status_code=500, detail="Project endpoint not available")

    try:
        goose_url = f"http://{endpoint}/api/v1/extensions/{extension_name}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.delete(goose_url)

            if response.status_code == 204:
                return {"message": "Extension deleted successfully"}
            elif response.status_code == 404:
                raise HTTPException(status_code=404, detail="Extension not found")
            elif response.status_code == 400:
                error_data = (
                    response.json()
                    if response.headers.get("content-type") == "application/json"
                    else {"detail": response.text}
                )
                raise HTTPException(
                    status_code=400,
                    detail=error_data.get("message")
                    or "Cannot delete enabled extension. Disable it first.",
                )
            else:
                error_data = (
                    response.json()
                    if response.headers.get("content-type") == "application/json"
                    else {"detail": response.text}
                )
                raise HTTPException(
                    status_code=response.status_code,
                    detail=error_data.get("message")
                    or error_data.get("detail")
                    or f"Failed to delete extension",
                )

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to connect to Goose API: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to delete extension: {str(e)}"
        )


@router.post(
    "/users/{user_id}/projects/{project_id}/messages", operation_id="send_message"
)
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
                    json={
                        "message": message.content
                    },  # Note: API expects "message" not "content"
                    headers={"Accept": "text/event-stream"},
                ) as response:
                    if response.status_code != 200:
                        error_text = await response.aread()
                        yield f'data: {{"error": "Goose API returned {response.status_code}: {error_text.decode()}"}}\n\n'
                        return

                    # Stream the Server-Sent Events
                    async for chunk in response.aiter_text():
                        # Parse each SSE chunk and extract the JSON content
                        lines = chunk.strip().split("\n")
                        for line in lines:
                            if line.startswith("data: "):
                                try:
                                    # Extract JSON from SSE data line
                                    json_str = line[6:]  # Remove 'data: ' prefix
                                    if json_str.strip():  # Skip empty data lines
                                        # Parse and re-emit the JSON
                                        parsed_data = json.loads(json_str)
                                        yield f"data: {json.dumps(parsed_data)}\n\n"
                                except json.JSONDecodeError:
                                    # If not valid JSON, pass through as-is
                                    yield f'data: {{"raw": {json.dumps(json_str)}}}\n\n'
                            elif line == "":
                                # Empty line - keep for SSE format
                                yield "\n"
                            else:
                                # Other SSE lines (like event:, id:, etc.)
                                yield f"{line}\n"

        return StreamingResponse(
            stream_response(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        )

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to connect to Goose API: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to proxy message: {str(e)}"
        )


@router.post(
    "/users/{user_id}/projects/{project_id}/messages/send",
    operation_id="send_message_fire_and_forget",
)
async def send_message_sync(user_id: str, project_id: str, message: MessageRequest):
    """
    Send message to a specific session without streaming (fire-and-forget).

    Args:
        user_id (str): The ID of the user who owns the project
        project_id (str): The ID of the project containing the session
        message (MessageRequest): Message request object containing:
            - session_id: ID of the session to send the message to
            - content: The message content to send

    Returns:
        dict: Response containing confirmation and result details
            - message: Success message
            - result: Result details from the Goose API
            - session_id: The ID of the session the message was sent to

    Raises:
        HTTPException:
            - 404: Project not found
            - 404: Session not found in project
            - 400: Project is not active
            - 500: Project endpoint not available
            - 500: Failed to connect to Goose API
            - Various status codes from the Goose API with corresponding error details

    Example:
        Sends message to the non-streaming endpoint of Goose API,
        waits for the complete response before returning (non-streaming)
    """
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
        # Forward to Goose API non-streaming endpoint
        goose_url = f"http://{endpoint}/api/v1/sessions/{message.session_id}/send"
        print(f"Sending message (fire-and-forget) to: {goose_url}")

        async with httpx.AsyncClient(
            timeout=120.0
        ) as client:  # Longer timeout for non-streaming
            response = await client.post(
                goose_url,
                json={"message": message.content},
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 200:
                result = response.json()
                return {
                    "message": "Message sent successfully",
                    "result": result,
                    "session_id": message.session_id,
                }
            else:
                error_data = (
                    response.json()
                    if response.headers.get("content-type") == "application/json"
                    else {"detail": response.text}
                )
                raise HTTPException(
                    status_code=response.status_code,
                    detail=error_data.get("message")
                    or error_data.get("detail")
                    or f"Goose API returned {response.status_code}",
                )

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to connect to Goose API: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send message: {str(e)}")


@router.get(
    "/users/{user_id}/projects/{project_id}/settings",
    operation_id="get_all_project_settings",
)
async def get_project_settings(user_id: str, project_id: str):
    """Get all settings for a project"""
    project = mongodb_service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Project belongs to different user")

    if project["status"] != "active":
        raise HTTPException(
            status_code=400, detail="Project must be active to manage settings"
        )

    endpoint = k8s_service.get_project_endpoint(user_id, project_id)
    if not endpoint:
        raise HTTPException(status_code=500, detail="Project endpoint not available")

    try:
        goose_url = f"http://{endpoint}/api/v1/settings"
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(goose_url)

            if response.status_code == 200:
                return response.json()
            else:
                error_text = response.text
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Goose API returned {response.status_code}: {error_text}",
                )

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to connect to Goose API: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch settings: {str(e)}"
        )


@router.get(
    "/users/{user_id}/projects/{project_id}/settings/{setting_key}",
    operation_id="get_specific_project_setting",
)
async def get_project_setting(user_id: str, project_id: str, setting_key: str):
    """Get a specific setting for a project"""
    project = mongodb_service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Project belongs to different user")

    if project["status"] != "active":
        raise HTTPException(
            status_code=400, detail="Project must be active to view settings"
        )

    endpoint = k8s_service.get_project_endpoint(user_id, project_id)
    if not endpoint:
        raise HTTPException(status_code=500, detail="Project endpoint not available")

    try:
        goose_url = f"http://{endpoint}/api/v1/settings/{setting_key}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(goose_url)

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                raise HTTPException(status_code=404, detail="Setting not found")
            else:
                error_text = response.text
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Goose API returned {response.status_code}: {error_text}",
                )

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to connect to Goose API: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch setting: {str(e)}"
        )


@router.put(
    "/users/{user_id}/projects/{project_id}/settings/{setting_key}",
    operation_id="update_project_setting",
)
async def update_project_setting(
    user_id: str, project_id: str, setting_key: str, setting_data: SettingUpdate
):
    """Update a specific setting for a project"""
    project = mongodb_service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Project belongs to different user")

    if project["status"] != "active":
        raise HTTPException(
            status_code=400, detail="Project must be active to update settings"
        )

    endpoint = k8s_service.get_project_endpoint(user_id, project_id)
    if not endpoint:
        raise HTTPException(status_code=500, detail="Project endpoint not available")

    try:
        goose_url = f"http://{endpoint}/api/v1/settings/{setting_key}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.put(goose_url, json=setting_data.dict())

            if response.status_code == 200:
                result = response.json()
                return {
                    "message": f"Setting {setting_key} updated successfully",
                    "setting": result,
                    "restart_required": result.get("restart_required", False),
                }
            elif response.status_code == 400:
                error_data = (
                    response.json()
                    if response.headers.get("content-type") == "application/json"
                    else {"detail": response.text}
                )
                raise HTTPException(
                    status_code=400,
                    detail=error_data.get("message")
                    or error_data.get("detail")
                    or "Invalid setting value",
                )
            elif response.status_code == 404:
                raise HTTPException(status_code=404, detail="Setting not found")
            else:
                error_data = (
                    response.json()
                    if response.headers.get("content-type") == "application/json"
                    else {"detail": response.text}
                )
                raise HTTPException(
                    status_code=response.status_code,
                    detail=error_data.get("message")
                    or error_data.get("detail")
                    or f"Failed to update setting",
                )

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to connect to Goose API: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to update setting: {str(e)}"
        )


@router.delete(
    "/users/{user_id}/projects/{project_id}/settings/{setting_key}",
    operation_id="reset_project_settings",
)
async def reset_project_setting(user_id: str, project_id: str, setting_key: str):
    """Reset a setting to its default value for a project"""
    project = mongodb_service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Project belongs to different user")

    if project["status"] != "active":
        raise HTTPException(
            status_code=400, detail="Project must be active to reset settings"
        )

    endpoint = k8s_service.get_project_endpoint(user_id, project_id)
    if not endpoint:
        raise HTTPException(status_code=500, detail="Project endpoint not available")

    try:
        goose_url = f"http://{endpoint}/api/v1/settings/{setting_key}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.delete(goose_url)

            if response.status_code == 200:
                result = response.json()
                return {
                    "message": f"Setting {setting_key} reset to default successfully",
                    "setting": result,
                }
            elif response.status_code == 404:
                raise HTTPException(status_code=404, detail="Setting not found")
            elif response.status_code == 400:
                error_data = (
                    response.json()
                    if response.headers.get("content-type") == "application/json"
                    else {"detail": response.text}
                )
                raise HTTPException(
                    status_code=400,
                    detail=error_data.get("message")
                    or "Cannot reset setting (may be overridden by environment variable)",
                )
            else:
                error_data = (
                    response.json()
                    if response.headers.get("content-type") == "application/json"
                    else {"detail": response.text}
                )
                raise HTTPException(
                    status_code=response.status_code,
                    detail=error_data.get("message")
                    or error_data.get("detail")
                    or f"Failed to reset setting",
                )

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to connect to Goose API: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to reset setting: {str(e)}"
        )


@router.put(
    "/users/{user_id}/projects/{project_id}/settings",
    operation_id="update_project_settings_in_bulk",
)
async def update_project_settings_bulk(
    user_id: str, project_id: str, settings_data: dict
):
    """Bulk update multiple settings for a project"""
    project = mongodb_service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Project belongs to different user")

    if project["status"] != "active":
        raise HTTPException(
            status_code=400, detail="Project must be active to update settings"
        )

    endpoint = k8s_service.get_project_endpoint(user_id, project_id)
    if not endpoint:
        raise HTTPException(status_code=500, detail="Project endpoint not available")

    try:
        goose_url = f"http://{endpoint}/api/v1/settings"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.put(goose_url, json=settings_data)

            if response.status_code == 200:
                result = response.json()
                return {
                    "message": f"Bulk settings update completed: {result.get('success_count', 0)}/{result.get('total_count', 0)} settings updated",
                    "result": result,
                }
            else:
                error_data = (
                    response.json()
                    if response.headers.get("content-type") == "application/json"
                    else {"detail": response.text}
                )
                raise HTTPException(
                    status_code=response.status_code,
                    detail=error_data.get("message")
                    or error_data.get("detail")
                    or f"Failed to update settings",
                )

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to connect to Goose API: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to update settings: {str(e)}"
        )
