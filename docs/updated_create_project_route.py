@router.post("/users/{user_id}/projects", operation_id="create_project")
async def create_project(user_id: str, project: ProjectCreate):
    """
    Create a new project with Kubernetes resources.

    Args:
        user_id (str): The ID of the user who owns the project
        project (ProjectCreate): Project creation data containing:
            - name: Name for the new project
            - github_key (optional): GitHub API key for repository access
            - repo_url (optional): GitHub repository URL to clone

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
        If repo_url is provided, repository will be cloned after pod is healthy
    """
    project_data = {
        "user_id": user_id,
        "name": project.name,
        "status": "inactive",
        "sessions": [],
        "github_key_set": bool(project.github_key),
        "repo_url": project.repo_url,
        "has_repository": bool(project.repo_url),
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

    # Create K8s resources and activate
    try:
        k8s_service.apply_project_resources(user_id, project_id, github_key)

        # Wait for pod to be ready - simple approach for POC
        await asyncio.sleep(30)

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

        # If repository URL is provided, clone it after pod is healthy
        if project.repo_url:
            try:
                print(f"📂 Cloning repository: {project.repo_url}")
                await k8s_service.clone_repository_on_pod(user_id, project_id, project.repo_url)
                print(f"✅ Repository cloned successfully")
            except Exception as e:
                print(f"❌ Repository cloning failed: {e}")
                # Don't fail the entire project creation, just log the error
                # The project is still usable without the repository
                pass

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