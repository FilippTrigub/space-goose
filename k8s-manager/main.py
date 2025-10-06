# Original main.py file - kept for local development
# For Vercel deployment, see api/index.py

import os
import uvicorn
from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

from fastapi_mcp import FastApiMCP

from dotenv import load_dotenv
load_dotenv()

from services import auth_service
from routes import project_routes

# Swagger UI Tags metadata
tags_metadata = [
    {
        "name": "Users",
        "description": "User management operations. Get available users in the system.",
    },
    {
        "name": "Projects",
        "description": "Project lifecycle management. Create, update, delete, activate and deactivate AI agent projects.",
    },
    {
        "name": "GitHub Integration",
        "description": "GitHub authentication and repository management for projects.",
    },
    {
        "name": "Sessions",
        "description": "AI conversation session management. Create and manage chat sessions with AI agents.",
    },
    {
        "name": "Messaging",
        "description": "Send messages to AI agents. Supports both streaming and fire-and-forget modes.",
    },
    {
        "name": "Extensions",
        "description": "Manage AI agent extensions. Add tools and capabilities to your AI agents.",
    },
    {
        "name": "Settings",
        "description": "Configure AI agent behavior and parameters.",
    },
    {
        "name": "Agent Status",
        "description": "Monitor AI agent health, activity, and performance metrics.",
    },
]

app = FastAPI(
    title="Space Goose K8s Manager API",
    version="1.0.0",
    description="""
    ## Space Goose K8s Manager
    
    A comprehensive API for managing Kubernetes-isolated AI agent environments. 
    This system allows you to:
    
    * **Create and manage projects** - Isolated AI agent environments
    * **GitHub integration** - Connect repositories to your AI agents  
    * **Session management** - Handle AI conversation sessions
    * **Real-time messaging** - Stream conversations with AI agents
    * **Extension system** - Add tools and capabilities to AI agents
    * **Settings control** - Configure AI behavior and parameters
    * **Resource monitoring** - Track agent status and performance
    
    ### Quick Start
    
    1. Get available users: `GET /users`
    2. Create a project: `POST /users/{user_id}/projects`
    3. Activate the project: `POST /users/{user_id}/projects/{project_id}/activate`
    4. Create a session: `POST /users/{user_id}/projects/{project_id}/sessions`
    5. Start chatting: `POST /users/{user_id}/projects/{project_id}/messages`
    
    ### Authentication
    
    Currently uses user IDs in path parameters. Authentication tokens will be added in future versions.
    
    ### Environments
    
    - **Development**: `http://localhost:8000`
    - **Swagger UI**: `http://localhost:8000/docs`
    - **ReDoc**: `http://localhost:8000/redoc`
    """,
    openapi_tags=tags_metadata,
    docs_url="/docs",
    redoc_url="/redoc",
    contact={
        "name": "Space Goose Team",
        "email": "contact@spacegoose.dev",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
)

# Add CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory="templates")

app.include_router(project_routes.router)


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


mcp = FastApiMCP(
    app,
    name="Space Goose MCP",
    description="Control remote goose coding agents",
    describe_all_responses=True,
    describe_full_response_schema=True,
    include_operations=[
        "get_user_projects",
        "create_project",
        "update_project",
        "delete_project",
        "activate_project",
        "deactivate_project",
        "update_project_github_key",
        "create_session",
        "get_all_project_sessions",
        "get_session_messages",
        "send_message_fire_and_forget",
        "get_all_project_settings",
        "get_specific_project_setting",
        "update_project_setting",
        "reset_project_settings",
        "update_project_settings_in_bulk",
    ],
    headers=["X-API-Key", "Authorization"],
)
mcp.mount_http()

if __name__ == "__main__":
    print(f"Running DEV MODE: {os.getenv('DEV_ENV') == '1'}")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
