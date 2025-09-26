from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class ProjectCreate(BaseModel):
    name: str
    github_key: Optional[str] = None

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
    sessions: Optional[List[Session]] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class User(BaseModel):
    id: str
    name: str

class ProjectUpdateGitHubKey(BaseModel):
    github_key: Optional[str] = None

class MessageRequest(BaseModel):
    content: str
    session_id: str
