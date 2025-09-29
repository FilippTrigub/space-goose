# Implementation Plan: API Route Documentation with Docstrings

## Overview
This plan outlines adding comprehensive docstrings to all API routes in `/home/filipp/space-goose/k8s-manager/routes/project_routes.py` to improve code documentation and API understanding.

## Current State Analysis
- **File**: `/home/filipp/space-goose/k8s-manager/routes/project_routes.py`
- **Current Routes**: 23 API endpoints
- **Documentation Status**: Most routes lack proper docstrings
- **Existing Docstrings**: Only 3 routes have docstrings currently

## Task 1: Add Docstrings to All Routes

### Routes Requiring Docstrings (20 routes):

#### User Management Routes
1. `GET /users` - `get_users()`
2. `GET /users/{user_id}/projects` - `get_projects()`

#### Project Management Routes  
3. `POST /users/{user_id}/projects` - `create_project()`
4. `PUT /users/{user_id}/projects/{project_id}` - `update_project()`
5. `DELETE /users/{user_id}/projects/{project_id}` - `delete_project()`
6. `POST /users/{user_id}/projects/{project_id}/activate` - `activate_project()`
7. `POST /users/{user_id}/projects/{project_id}/deactivate` - `deactivate_project()`

#### Session Management Routes
8. `POST /users/{user_id}/projects/{project_id}/sessions` - `create_session()` ✅ (has docstring)
9. `GET /users/{user_id}/projects/{project_id}/sessions` - `get_project_sessions()` ✅ (has docstring)
10. `DELETE /users/{user_id}/projects/{project_id}/sessions/{session_id}` - `delete_session()` ✅ (has docstring)
11. `GET /users/{user_id}/projects/{project_id}/sessions/{session_id}/messages` - `get_session_messages()` ✅ (has docstring)

#### Extension Management Routes
12. `GET /users/{user_id}/projects/{project_id}/extensions` - `get_project_extensions()`
13. `POST /users/{user_id}/projects/{project_id}/extensions` - `create_project_extension()`
14. `PUT /users/{user_id}/projects/{project_id}/extensions/{extension_name}/toggle` - `toggle_project_extension()`
15. `DELETE /users/{user_id}/projects/{project_id}/extensions/{extension_name}` - `delete_project_extension()`

#### Messaging Routes
16. `POST /users/{user_id}/projects/{project_id}/messages` - `proxy_message()` ✅ (has docstring)
17. `POST /users/{user_id}/projects/{project_id}/messages/send` - `send_message_sync()`

#### Settings Management Routes
18. `GET /users/{user_id}/projects/{project_id}/settings` - `get_project_settings()` ✅ (has docstring)
19. `GET /users/{user_id}/projects/{project_id}/settings/{setting_key}` - `get_project_setting()` ✅ (has docstring)
20. `PUT /users/{user_id}/projects/{project_id}/settings/{setting_key}` - `update_project_setting()` ✅ (has docstring)
21. `DELETE /users/{user_id}/projects/{project_id}/settings/{setting_key}` - `reset_project_setting()` ✅ (has docstring)
22. `PUT /users/{user_id}/projects/{project_id}/settings` - `update_project_settings_bulk()` ✅ (has docstring)

#### GitHub Integration Routes
23. `PUT /users/{user_id}/projects/{project_id}/github-key` - `update_project_github_key()` ✅ (has docstring)

### Docstring Format Standard

Each docstring should follow this format:
```python
"""
Brief description of what the endpoint does.

Args:
    param1 (type): Description of parameter
    param2 (type): Description of parameter
    
Returns:
    dict: Description of return value structure
    
Raises:
    HTTPException: When and why exceptions are raised
    
Example:
    Brief usage example or important notes
"""
```

## Implementation Steps

### Step 1: User Management Routes
- Add docstring to `get_users()` - Returns list of available users
- Add docstring to `get_projects()` - Lists all projects for a specific user

### Step 2: Project Management Routes  
- Add docstring to `create_project()` - Creates new project with K8s resources
- Add docstring to `update_project()` - Updates project name and metadata
- Add docstring to `delete_project()` - Removes project and all K8s resources  
- Add docstring to `activate_project()` - Scales up deployment and gets endpoint
- Add docstring to `deactivate_project()` - Scales down deployment

### Step 3: Extension Management Routes
- Add docstring to `get_project_extensions()` - Lists all extensions for active project
- Add docstring to `create_project_extension()` - Creates new extension (stdio/HTTP)
- Add docstring to `toggle_project_extension()` - Enables/disables extension
- Add docstring to `delete_project_extension()` - Removes extension from project

### Step 4: Messaging Routes  
- Add docstring to `send_message_sync()` - Fire-and-forget message sending

### Step 5: Helper Functions
- Add docstring to `update_project_env_vars()` - Updates K8s environment variables

## Quality Standards

### Content Requirements
- **Purpose**: Clear, one-line summary of the endpoint's function
- **Parameters**: Document all path, query, and body parameters with types
- **Returns**: Describe the response structure and HTTP status codes
- **Exceptions**: Document all possible HTTPException scenarios
- **Context**: Include important behavioral notes (e.g., "Project must be active")

### Examples of Good Docstrings
```python
"""
Create a new project with Kubernetes resources.

Creates a project with associated K8s deployment, service, and configmap.
The project starts in 'inactive' status and must be activated separately.

Args:
    user_id (str): ID of the user creating the project
    project (ProjectCreate): Project creation data including name and optional GitHub key
    
Returns:
    dict: Success message and project_id
    
Raises:
    HTTPException 500: If K8s resource creation fails
    HTTPException 400: If project data is invalid
    
Note:
    If GitHub key is provided, it's stored securely in K8s secrets.
"""
```

## Deliverables

1. **Updated project_routes.py** with comprehensive docstrings
2. **Consistent documentation style** across all routes  
3. **Clear API behavior documentation** for frontend integration
4. **Better developer experience** for future maintenance

## Success Criteria

- ✅ All 20+ routes have comprehensive docstrings
- ✅ Docstrings follow consistent format and style
- ✅ All parameters, returns, and exceptions are documented
- ✅ Code remains functionally unchanged
- ✅ Documentation aids in API understanding and maintenance

## Estimated Effort

- **Time**: 2-3 hours
- **Complexity**: Low (documentation only, no logic changes)
- **Risk**: Very low (no functional changes)
- **Dependencies**: None