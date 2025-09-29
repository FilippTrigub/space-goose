# Original main.py file - kept for local development
# For Vercel deployment, see api/index.py

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

from fastapi_mcp import FastApiMCP

from routes import project_routes

app = FastAPI(
    title="K8s Environment Manager",
    version="0.1.0",
    description="A PoC application for managing Kubernetes-isolated user environments",
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
)
mcp.mount_http()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
