# Project Routes API Documentation

This document provides comprehensive API documentation for the Space Goose K8s Manager project routes, including test curl commands using `user1` as the test user.

## Base URL
```
http://localhost:8000
```

---

## Complete Workflow Example

Here's a complete workflow using user1 to create and interact with a project:

```bash

# 1. Create a project
PROJECT_RESPONSE=$(curl -s -X POST "http://localhost:8000/users/user1/projects" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Workflow Project",
    "repo_url": "https://github.com/microsoft/TypeScript"
  }')

# Extract project ID (assuming jq is available)
PROJECT_ID=$(echo $PROJECT_RESPONSE | jq -r '.project_id')

# 42. Create a session
SESSION_RESPONSE=$(curl -s -X POST "http://localhost:8000/users/user1/projects/$PROJECT_ID/sessions" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Session"
  }')

# Extract session ID
SESSION_ID=$(echo $SESSION_RESPONSE | jq -r '.session.session_id')

# 3. Send a message
curl -X POST "http://localhost:8000/users/user1/projects/$PROJECT_ID/messages" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "'$SESSION_ID'",
    "content": "Hello! Can you help me understand the codebase?"
  }'

# 4. Get agent status
curl -X GET "http://localhost:8000/users/user1/projects/$PROJECT_ID/agent/status" \
  -H "Content-Type: application/json"

# 5. Get session messages
curl -X GET "http://localhost:8000/users/user1/projects/$PROJECT_ID/sessions/$SESSION_ID/messages" \
  -H "Content-Type: application/json"

# 6. Deactivate project when done
curl -X POST "http://localhost:8000/users/user1/projects/$PROJECT_ID/deactivate" \
  -H "Content-Type: application/json"
```

---

## 1. Users Management

### Get All Users
Retrieve a list of all available users (MVP static list).

**Endpoint:** `GET /users`

**Response:**
```json
[
  {
    "id": "user1",
    "name": "User 1"
  },
  {
    "id": "user2", 
    "name": "User 2"
  }
]
```

**Test Command:**
```bash
curl -X GET "http://localhost:8000/users" \
  -H "Content-Type: application/json"
```

---

## 2. Projects Management

### Get User Projects
Retrieve all projects for a specific user.

**Endpoint:** `GET /users/{user_id}/projects`

**Parameters:**
- `user_id` (path): The ID of the user (e.g., "user1")

**Response:**
```json
[
  {
    "id": "project_id_123",
    "user_id": "user1",
    "name": "My AI Project",
    "status": "active",
    "endpoint": "192.168.1.100:8080",
    "github_key_set": true,
    "github_key_source": "user",
    "repo_url": "https://github.com/user/repo",
    "has_repository": true,
    "sessions": [],
    "created_at": "2023-12-01T10:00:00Z",
    "updated_at": "2023-12-01T10:00:00Z"
  }
]
```

**Test Command:**
```bash
curl -X GET "http://localhost:8000/users/user1/projects" \
  -H "Content-Type: application/json"
```

### Create Project
Create a new project with Kubernetes resources.

**Endpoint:** `POST /users/{user_id}/projects`

**Parameters:**
- `user_id` (path): The ID of the user

**Request Body:**
```json
{
  "name": "My New Project",
  "github_key": "ghp_xxxxxxxxxxxxxxxxxxxx",
  "repo_url": "https://github.com/user/my-repo"
}
```

**Response:**
```json
{
  "message": "Project created successfully",
  "project_id": "generated_project_id"
}
```

**Test Commands:**

Basic project creation:
```bash
curl -X POST "http://localhost:8000/users/user1/projects" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Project Basic"
  }'
```

Project with GitHub repository:
```bash
curl -X POST "http://localhost:8000/users/user1/projects" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Project with Repo",
    "github_key": "ghp_your_github_token_here",
    "repo_url": "https://github.com/microsoft/TypeScript"
  }'
```

### Update Project
Update an existing project's name and metadata.

**Endpoint:** `PUT /users/{user_id}/projects/{project_id}`

**Parameters:**
- `user_id` (path): The ID of the user
- `project_id` (path): The ID of the project

**Request Body:**
```json
{
  "name": "Updated Project Name"
}
```

**Response:**
```json
{
  "message": "Project updated successfully"
}
```

**Test Command:**
```bash
curl -X PUT "http://localhost:8000/users/user1/projects/PROJECT_ID_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Updated Test Project"
  }'
```

### Delete Project
Delete a project and all its associated Kubernetes resources.

**Endpoint:** `DELETE /users/{user_id}/projects/{project_id}`

**Parameters:**
- `user_id` (path): The ID of the user
- `project_id` (path): The ID of the project

**Response:**
```json
{
  "message": "Project deleted successfully"
}
```

**Test Command:**
```bash
curl -X DELETE "http://localhost:8000/users/user1/projects/PROJECT_ID_HERE" \
  -H "Content-Type: application/json"
```

### Activate Project
Activate a project by scaling up its deployment.

**Endpoint:** `POST /users/{user_id}/projects/{project_id}/activate`

**Parameters:**
- `user_id` (path): The ID of the user
- `project_id` (path): The ID of the project

**Response:**
```json
{
  "message": "Project activated successfully",
  "endpoint": "192.168.1.100:8080"
}
```

**Test Command:**
```bash
curl -X POST "http://localhost:8000/users/user1/projects/PROJECT_ID_HERE/activate" \
  -H "Content-Type: application/json"
```

### Deactivate Project
Deactivate a project by scaling down its deployment.

**Endpoint:** `POST /users/{user_id}/projects/{project_id}/deactivate`

**Parameters:**
- `user_id` (path): The ID of the user
- `project_id` (path): The ID of the project

**Response:**
```json
{
  "message": "Project deactivated successfully"
}
```

**Test Command:**
```bash
curl -X POST "http://localhost:8000/users/user1/projects/PROJECT_ID_HERE/deactivate" \
  -H "Content-Type: application/json"
```

### Clone Repository
Manually clone the repository for an active project.

**Endpoint:** `POST /users/{user_id}/projects/{project_id}/clone-repository`

**Parameters:**
- `user_id` (path): The ID of the user
- `project_id` (path): The ID of the project

**Response:**
```json
{
  "message": "Repository https://github.com/user/repo cloned successfully"
}
```

**Test Command:**
```bash
curl -X POST "http://localhost:8000/users/user1/projects/PROJECT_ID_HERE/clone-repository" \
  -H "Content-Type: application/json"
```

---

## 3. GitHub Integration

### Update Project GitHub Key
Update GitHub key for an existing project.

**Endpoint:** `PUT /users/{user_id}/projects/{project_id}/github-key`

**Parameters:**
- `user_id` (path): The ID of the user
- `project_id` (path): The ID of the project

**Request Body:**
```json
{
  "github_key": "ghp_new_github_token_here"
}
```

**Response:**
```json
{
  "message": "GitHub key updated successfully"
}
```

**Test Commands:**

Set GitHub key:
```bash
curl -X PUT "http://localhost:8000/users/user1/projects/PROJECT_ID_HERE/github-key" \
  -H "Content-Type: application/json" \
  -d '{
    "github_key": "ghp_your_new_github_token"
  }'
```

Remove GitHub key:
```bash
curl -X PUT "http://localhost:8000/users/user1/projects/PROJECT_ID_HERE/github-key" \
  -H "Content-Type: application/json" \
  -d '{
    "github_key": null
  }'
```

### Update User Global GitHub Key
Set or update the global GitHub key for a user.

**Endpoint:** `PUT /users/{user_id}/github-key`

**Parameters:**
- `user_id` (path): The ID of the user

**Request Body:**
```json
{
  "github_key": "ghp_global_github_token"
}
```

**Response:**
```json
{
  "message": "Global GitHub key set successfully"
}
```

**Test Commands:**

Set global GitHub key:
```bash
curl -X PUT "http://localhost:8000/users/user1/github-key" \
  -H "Content-Type: application/json" \
  -d '{
    "github_key": "ghp_your_global_github_token"
  }'
```

Remove global GitHub key:
```bash
curl -X PUT "http://localhost:8000/users/user1/github-key" \
  -H "Content-Type: application/json" \
  -d '{
    "github_key": null
  }'
```

### Check User Global GitHub Key
Check if a user has a global GitHub key set.

**Endpoint:** `GET /users/{user_id}/github-key`

**Parameters:**
- `user_id` (path): The ID of the user

**Response:**
```json
{
  "github_key_set": true
}
```

**Test Command:**
```bash
curl -X GET "http://localhost:8000/users/user1/github-key" \
  -H "Content-Type: application/json"
```

### Delete User Global GitHub Key
Remove the global GitHub key for a user.

**Endpoint:** `DELETE /users/{user_id}/github-key`

**Parameters:**
- `user_id` (path): The ID of the user

**Response:**
```json
{
  "message": "Global GitHub key removed successfully"
}
```

**Test Command:**
```bash
curl -X DELETE "http://localhost:8000/users/user1/github-key" \
  -H "Content-Type: application/json"
```

---

## 4. Session Management

### Create Session
Create a new session in the Goose API and store it in the project.

**Endpoint:** `POST /users/{user_id}/projects/{project_id}/sessions`

**Parameters:**
- `user_id` (path): The ID of the user
- `project_id` (path): The ID of the project

**Request Body:**
```json
{
  "name": "My AI Session"
}
```

**Response:**
```json
{
  "message": "Session created successfully",
  "session": {
    "session_id": "generated_session_id",
    "name": "My AI Session",
    "created_at": "2023-12-01T10:00:00Z",
    "message_count": 0
  }
}
```

**Test Command:**
```bash
curl -X POST "http://localhost:8000/users/user1/projects/PROJECT_ID_HERE/sessions" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test AI Session"
  }'
```

### Get Project Sessions
Get all sessions for a project.

**Endpoint:** `GET /users/{user_id}/projects/{project_id}/sessions`

**Parameters:**
- `user_id` (path): The ID of the user
- `project_id` (path): The ID of the project

**Response:**
```json
{
  "sessions": [
    {
      "session_id": "session_123",
      "name": "My AI Session",
      "created_at": "2023-12-01T10:00:00Z",
      "message_count": 5
    }
  ]
}
```

**Test Command:**
```bash
curl -X GET "http://localhost:8000/users/user1/projects/PROJECT_ID_HERE/sessions" \
  -H "Content-Type: application/json"
```

### Delete Session
Delete a session from both Goose API and project data.

**Endpoint:** `DELETE /users/{user_id}/projects/{project_id}/sessions/{session_id}`

**Parameters:**
- `user_id` (path): The ID of the user
- `project_id` (path): The ID of the project
- `session_id` (path): The ID of the session

**Response:**
```json
{
  "message": "Session deleted successfully"
}
```

**Test Command:**
```bash
curl -X DELETE "http://localhost:8000/users/user1/projects/PROJECT_ID_HERE/sessions/SESSION_ID_HERE" \
  -H "Content-Type: application/json"
```

### Get Session Messages
Get message history for a session.

**Endpoint:** `GET /users/{user_id}/projects/{project_id}/sessions/{session_id}/messages`

**Parameters:**
- `user_id` (path): The ID of the user
- `project_id` (path): The ID of the project
- `session_id` (path): The ID of the session

**Response:**
```json
{
  "session_id": "session_123",
  "messages": [
    {
      "id": "msg_1",
      "content": "Hello, AI assistant!",
      "role": "user",
      "timestamp": "2023-12-01T10:00:00Z"
    },
    {
      "id": "msg_2", 
      "content": "Hello! How can I help you today?",
      "role": "assistant",
      "timestamp": "2023-12-01T10:00:05Z"
    }
  ],
  "total_count": 2
}
```

**Test Command:**
```bash
curl -X GET "http://localhost:8000/users/user1/projects/PROJECT_ID_HERE/sessions/SESSION_ID_HERE/messages" \
  -H "Content-Type: application/json"
```

### Send Message (Streaming)
Send message to a specific session and stream the response.

**Endpoint:** `POST /users/{user_id}/projects/{project_id}/messages`

**Parameters:**
- `user_id` (path): The ID of the user
- `project_id` (path): The ID of the project

**Request Body:**
```json
{
  "session_id": "session_123",
  "content": "Hello, can you help me with Python?"
}
```

**Response:** Server-Sent Events stream

**Test Command:**
```bash
curl -X POST "http://localhost:8000/users/user1/projects/PROJECT_ID_HERE/messages" \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{
    "session_id": "SESSION_ID_HERE",
    "content": "Hello, can you help me write a Python function?"
  }'
```

### Send Message (Fire-and-Forget)
Send message to a specific session without streaming.

**Endpoint:** `POST /users/{user_id}/projects/{project_id}/messages/send`

**Parameters:**
- `user_id` (path): The ID of the user
- `project_id` (path): The ID of the project

**Request Body:**
```json
{
  "session_id": "session_123",
  "content": "What is machine learning?"
}
```

**Response:**
```json
{
  "message": "Message sent successfully",
  "result": {
    "response": "Machine learning is a subset of artificial intelligence...",
    "tokens_used": 150,
    "processing_time": 2.5
  },
  "session_id": "session_123"
}
```

**Test Command:**
```bash
curl -X POST "http://localhost:8000/users/user1/projects/PROJECT_ID_HERE/messages/send" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "SESSION_ID_HERE",
    "content": "Explain machine learning in simple terms"
  }'
```

---

## 5. Extension Management

### Get Project Extensions
Get all extensions for a project.

**Endpoint:** `GET /users/{user_id}/projects/{project_id}/extensions`

**Parameters:**
- `user_id` (path): The ID of the user
- `project_id` (path): The ID of the project

**Response:**
```json
{
  "extensions": [
    {
      "name": "filesystem",
      "type": "stdio",
      "enabled": true,
      "description": "File system operations"
    },
    {
      "name": "web_search",
      "type": "streamable_http",
      "enabled": false,
      "description": "Web search capabilities"
    }
  ]
}
```

**Test Command:**
```bash
curl -X GET "http://localhost:8000/users/user1/projects/PROJECT_ID_HERE/extensions" \
  -H "Content-Type: application/json"
```

### Create Project Extension
Create a new extension for a project.

**Endpoint:** `POST /users/{user_id}/projects/{project_id}/extensions`

**Parameters:**
- `user_id` (path): The ID of the user
- `project_id` (path): The ID of the project

**Request Body for STDIO Extension:**
```json
{
  "name": "my_tool",
  "extension_type": "stdio",
  "description": "My custom tool",
  "args": ["create-next-app", "my-app"],
  "envs": {
    "NODE_ENV": "development",
    "API_KEY": "your_api_key"
  }
}
```

**Request Body for HTTP Extension:**
```json
{
  "name": "web_api",
  "extension_type": "streamable_http",
  "description": "Web API extension",
  "uri": "http://api.example.com/webhook",
  "envs": {
    "API_TOKEN": "your_token"
  }
}
```

**Response:**
```json
{
  "message": "Extension created successfully. Pod restarting with new environment variables."
}
```

**Test Commands:**

Create STDIO extension:
```bash
curl -X POST "http://localhost:8000/users/user1/projects/PROJECT_ID_HERE/extensions" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "test_stdio",
    "extension_type": "stdio",
    "description": "Test STDIO extension",
    "args": ["express", "test-app"],
    "envs": {
      "NODE_ENV": "development"
    }
  }'
```

Create HTTP extension:
```bash
curl -X POST "http://localhost:8000/users/user1/projects/PROJECT_ID_HERE/extensions" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "test_http",
    "extension_type": "streamable_http", 
    "description": "Test HTTP extension",
    "uri": "http://httpbin.org/post",
    "envs": {
      "TEST_VAR": "test_value"
    }
  }'
```

### Toggle Project Extension
Toggle extension enabled/disabled for a project.

**Endpoint:** `PUT /users/{user_id}/projects/{project_id}/extensions/{extension_name}/toggle`

**Parameters:**
- `user_id` (path): The ID of the user
- `project_id` (path): The ID of the project
- `extension_name` (path): The name of the extension

**Request Body:**
```json
{
  "enabled": true
}
```

**Response:**
```json
{
  "message": "Extension enabled successfully",
  "extension": {
    "name": "filesystem",
    "enabled": true,
    "type": "stdio"
  }
}
```

**Test Commands:**

Enable extension:
```bash
curl -X PUT "http://localhost:8000/users/user1/projects/PROJECT_ID_HERE/extensions/EXTENSION_NAME/toggle" \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": true
  }'
```

Disable extension:
```bash
curl -X PUT "http://localhost:8000/users/user1/projects/PROJECT_ID_HERE/extensions/EXTENSION_NAME/toggle" \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": false
  }'
```

### Delete Project Extension
Delete an extension from a project.

**Endpoint:** `DELETE /users/{user_id}/projects/{project_id}/extensions/{extension_name}`

**Parameters:**
- `user_id` (path): The ID of the user
- `project_id` (path): The ID of the project
- `extension_name` (path): The name of the extension

**Response:**
```json
{
  "message": "Extension deleted successfully"
}
```

**Test Command:**
```bash
curl -X DELETE "http://localhost:8000/users/user1/projects/PROJECT_ID_HERE/extensions/EXTENSION_NAME" \
  -H "Content-Type: application/json"
```

---

## 6. Settings Management

### Get All Project Settings
Get all settings for a project.

**Endpoint:** `GET /users/{user_id}/projects/{project_id}/settings`

**Parameters:**
- `user_id` (path): The ID of the user
- `project_id` (path): The ID of the project

**Response:**
```json
{
  "settings": [
    {
      "key": "model",
      "value": "gpt-4",
      "type": "string",
      "description": "AI model to use",
      "default_value": "gpt-3.5-turbo"
    },
    {
      "key": "temperature",
      "value": 0.7,
      "type": "float", 
      "description": "Model temperature",
      "default_value": 0.5
    }
  ]
}
```

**Test Command:**
```bash
curl -X GET "http://localhost:8000/users/user1/projects/PROJECT_ID_HERE/settings" \
  -H "Content-Type: application/json"
```

### Get Specific Project Setting
Get a specific setting for a project.

**Endpoint:** `GET /users/{user_id}/projects/{project_id}/settings/{setting_key}`

**Parameters:**
- `user_id` (path): The ID of the user
- `project_id` (path): The ID of the project
- `setting_key` (path): The key of the setting

**Response:**
```json
{
  "key": "model",
  "value": "gpt-4",
  "type": "string",
  "description": "AI model to use",
  "default_value": "gpt-3.5-turbo"
}
```

**Test Command:**
```bash
curl -X GET "http://localhost:8000/users/user1/projects/PROJECT_ID_HERE/settings/model" \
  -H "Content-Type: application/json"
```

### Update Project Setting
Update a specific setting for a project.

**Endpoint:** `PUT /users/{user_id}/projects/{project_id}/settings/{setting_key}`

**Parameters:**
- `user_id` (path): The ID of the user
- `project_id` (path): The ID of the project
- `setting_key` (path): The key of the setting

**Request Body:**
```json
{
  "value": "gpt-4"
}
```

**Response:**
```json
{
  "message": "Setting model updated successfully",
  "setting": {
    "key": "model",
    "value": "gpt-4",
    "type": "string"
  },
  "restart_required": false
}
```

**Test Commands:**

Update string setting:
```bash
curl -X PUT "http://localhost:8000/users/user1/projects/PROJECT_ID_HERE/settings/model" \
  -H "Content-Type: application/json" \
  -d '{
    "value": "gpt-4"
  }'
```

Update numeric setting:
```bash
curl -X PUT "http://localhost:8000/users/user1/projects/PROJECT_ID_HERE/settings/temperature" \
  -H "Content-Type: application/json" \
  -d '{
    "value": 0.8
  }'
```

### Reset Project Setting
Reset a setting to its default value for a project.

**Endpoint:** `DELETE /users/{user_id}/projects/{project_id}/settings/{setting_key}`

**Parameters:**
- `user_id` (path): The ID of the user
- `project_id` (path): The ID of the project
- `setting_key` (path): The key of the setting

**Response:**
```json
{
  "message": "Setting model reset to default successfully",
  "setting": {
    "key": "model",
    "value": "gpt-3.5-turbo",
    "type": "string"
  }
}
```

**Test Command:**
```bash
curl -X DELETE "http://localhost:8000/users/user1/projects/PROJECT_ID_HERE/settings/model" \
  -H "Content-Type: application/json"
```

### Bulk Update Project Settings
Bulk update multiple settings for a project.

**Endpoint:** `PUT /users/{user_id}/projects/{project_id}/settings`

**Parameters:**
- `user_id` (path): The ID of the user
- `project_id` (path): The ID of the project

**Request Body:**
```json
{
  "model": "gpt-4",
  "temperature": 0.8,
  "max_tokens": 2048
}
```

**Response:**
```json
{
  "message": "Bulk settings update completed: 3/3 settings updated",
  "result": {
    "success_count": 3,
    "total_count": 3,
    "errors": []
  }
}
```

**Test Command:**
```bash
curl -X PUT "http://localhost:8000/users/user1/projects/PROJECT_ID_HERE/settings" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4",
    "temperature": 0.9,
    "max_tokens": 4096
  }'
```

---

## 7. Agent Status

### Get Agent Status
Get the current status of the AI agent for a project.

**Endpoint:** `GET /users/{user_id}/projects/{project_id}/agent/status`

**Parameters:**
- `user_id` (path): The ID of the user
- `project_id` (path): The ID of the project

**Response:**
```json
{
  "overall_status": "running",
  "active_sessions": 2,
  "total_processed": 45,
  "uptime_seconds": 3600,
  "sessions": [
    {
      "session_id": "session_123",
      "status": "active",
      "message_count": 10
    },
    {
      "session_id": "session_456", 
      "status": "idle",
      "message_count": 5
    }
  ],
  "project_status": "active"
}
```

**Test Command:**
```bash
curl -X GET "http://localhost:8000/users/user1/projects/PROJECT_ID_HERE/agent/status" \
  -H "Content-Type: application/json"
```

---

## Error Responses

All endpoints may return the following error responses:

### 400 Bad Request
```json
{
  "detail": "Project must be active to create sessions"
}
```

### 403 Forbidden
```json
{
  "detail": "Project belongs to different user"
}
```

### 404 Not Found
```json
{
  "detail": "Project not found"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Failed to create K8s resources: Connection timeout"
}
```


---

## Notes

- **Project Status**: Projects must be "active" to create sessions, send messages, or manage extensions
- **Authentication**: This API currently uses user IDs in the path rather than authentication tokens
- **Streaming**: The streaming message endpoint uses Server-Sent Events (SSE)
- **GitHub Integration**: Supports both project-specific and global user GitHub keys
- **Kubernetes**: All projects run in Kubernetes pods with dynamic scaling
- **Repository Cloning**: Repositories are automatically cloned when projects are created or activated (if repo_url is provided)

Replace `PROJECT_ID_HERE`, `SESSION_ID_HERE`, and `EXTENSION_NAME` with actual values when testing.