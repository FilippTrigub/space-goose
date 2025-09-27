from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime

class ProjectCreate(BaseModel):
    name: str
    github_key: Optional[str] = None
    use_global_github_key: Optional[bool] = True

class ProjectUpdate(BaseModel):
    name: str

class SessionCreate(BaseModel):
    name: Optional[str] = None

class Session(BaseModel):
    session_id: str
    name: Optional[str] = None
    created_at: Optional[datetime] = None
    message_count: Optional[int] = 0

class Project(BaseModel):
    id: str
    user_id: str
    name: str
    status: str  # active, inactive
    endpoint: Optional[str] = None
    github_key_set: Optional[bool] = False
    github_key_source: Optional[str] = None  # "project" or "user"
    sessions: Optional[List[Session]] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class User(BaseModel):
    id: str
    name: str

class UserGitHubKey(BaseModel):
    github_key: str

class ProjectUpdateGitHubKey(BaseModel):
    github_key: Optional[str] = None

class Extension(BaseModel):
    name: str
    display_name: Optional[str] = None
    extension_type: str  # builtin, stdio, sse, streamable_http, frontend, inline_python
    enabled: bool
    timeout: Optional[int] = None
    description: Optional[str] = None
    # Type-specific fields
    cmd: Optional[str] = None
    args: Optional[List[str]] = None
    bundled: Optional[bool] = None
    uri: Optional[str] = None
    python_code: Optional[str] = None
    envs: Optional[dict] = None
    env_keys: Optional[List[str]] = None
    headers: Optional[dict] = None

class ExtensionCreate(BaseModel):
    name: str
    display_name: Optional[str] = None
    extension_type: str  # stdio, streamable_http
    description: Optional[str] = None
    # For stdio extensions (npx only)
    args: Optional[List[str]] = None
    # For http extensions
    uri: Optional[str] = None
    # Environment variables for K8s pod
    envs: Optional[dict] = None

class ExtensionToggle(BaseModel):
    enabled: bool

class MessageRequest(BaseModel):
    content: str
    session_id: str

class SettingUpdate(BaseModel):
    value: Any  # Can be string, number, or boolean