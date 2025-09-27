import os
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB")
PROJECTS_COLLECTION = "projects"
USERS_COLLECTION = "users"

client = MongoClient(MONGO_URI)
db = client[MONGO_DB]

def get_projects_collection():
    return db[PROJECTS_COLLECTION]

def get_users_collection():
    return db[USERS_COLLECTION]

def list_projects(user_id: str):
    return list(get_projects_collection().find({"user_id": user_id}))

def create_project(project_data: dict):
    # Initialize sessions array if not present
    if "sessions" not in project_data:
        project_data["sessions"] = []
    return get_projects_collection().insert_one(project_data)

def get_project(project_id: str):
    try:
        return get_projects_collection().find_one({"_id": ObjectId(project_id)})
    except:
        return None

def update_project(project_id: str, update_data: dict):
    return get_projects_collection().update_one(
        {"_id": ObjectId(project_id)},
        {"$set": update_data}
    )

def update_project_status(project_id: str, status: str, endpoint: str = None):
    update_data = {
        "status": status,
        "updated_at": datetime.utcnow()
    }
    if endpoint:
        update_data["endpoint"] = endpoint
    elif status == "inactive":
        update_data["endpoint"] = None
    
    return get_projects_collection().update_one(
        {"_id": ObjectId(project_id)},
        {"$set": update_data}
    )

def add_session_to_project(project_id: str, session_data: dict):
    """Add a session to a project's sessions array"""
    return get_projects_collection().update_one(
        {"_id": ObjectId(project_id)},
        {
            "$push": {"sessions": session_data},
            "$set": {"updated_at": datetime.utcnow()}
        }
    )

def remove_session_from_project(project_id: str, session_id: str):
    """Remove a session from a project's sessions array"""
    return get_projects_collection().update_one(
        {"_id": ObjectId(project_id)},
        {
            "$pull": {"sessions": {"session_id": session_id}},
            "$set": {"updated_at": datetime.utcnow()}
        }
    )

def update_session_in_project(project_id: str, session_id: str, session_data: dict):
    """Update a specific session in a project's sessions array"""
    return get_projects_collection().update_one(
        {"_id": ObjectId(project_id), "sessions.session_id": session_id},
        {
            "$set": {
                "sessions.$.name": session_data.get("name"),
                "sessions.$.message_count": session_data.get("message_count", 0),
                "updated_at": datetime.utcnow()
            }
        }
    )

def store_github_key(project_id: str, github_key: str, source: str = "project"):
    """Store GitHub key for a project (masked for security)"""
    # Store only a masked version for reference
    masked_key = f"{github_key[:8]}{'*' * (len(github_key) - 12)}{github_key[-4:]}" if len(github_key) > 12 else "*" * len(github_key)
    return get_projects_collection().update_one(
        {"_id": ObjectId(project_id)},
        {
            "$set": {
                "github_key_masked": masked_key,
                "github_key_set": True,
                "github_key_source": source,
                "updated_at": datetime.utcnow()
            }
        }
    )

def update_github_key(project_id: str, github_key: str = None):
    """Update GitHub key for a project"""
    if github_key:
        # Store masked version for reference
        masked_key = f"{github_key[:8]}{'*' * (len(github_key) - 12)}{github_key[-4:]}" if len(github_key) > 12 else "*" * len(github_key)
        update_data = {
            "github_key_masked": masked_key,
            "github_key_set": True,
            "github_key_source": "project",
            "updated_at": datetime.utcnow()
        }
    else:
        # Remove GitHub key
        update_data = {
            "$unset": {"github_key_masked": ""},
            "github_key_set": False,
            "github_key_source": None,
            "updated_at": datetime.utcnow()
        }
    
    return get_projects_collection().update_one(
        {"_id": ObjectId(project_id)},
        {"$set": update_data} if github_key else update_data
    )

def delete_project(project_id: str):
    return get_projects_collection().delete_one({"_id": ObjectId(project_id)})

# User-level GitHub token functions
def get_user(user_id: str):
    """Get user document or create it if it doesn't exist"""
    user = get_users_collection().find_one({"user_id": user_id})
    if not user:
        # Create user document if it doesn't exist
        get_users_collection().insert_one({
            "user_id": user_id,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        })
        user = get_users_collection().find_one({"user_id": user_id})
    return user

def store_user_github_key(user_id: str, github_key: str):
    """Store GitHub key for a user (masked for security)"""
    # Store only a masked version for reference
    masked_key = f"{github_key[:8]}{'*' * (len(github_key) - 12)}{github_key[-4:]}" if len(github_key) > 12 else "*" * len(github_key)
    
    # Ensure user exists
    get_user(user_id)
    
    return get_users_collection().update_one(
        {"user_id": user_id},
        {
            "$set": {
                "github_key_masked": masked_key,
                "github_key_set": True,
                "updated_at": datetime.utcnow()
            }
        }
    )

def get_user_github_key_status(user_id: str):
    """Check if a user has a GitHub key set"""
    user = get_user(user_id)
    return {
        "github_key_set": user.get("github_key_set", False),
        "github_key_masked": user.get("github_key_masked", None)
    }

def delete_user_github_key(user_id: str):
    """Delete GitHub key for a user"""
    return get_users_collection().update_one(
        {"user_id": user_id},
        {
            "$unset": {"github_key_masked": ""},
            "$set": {
                "github_key_set": False,
                "updated_at": datetime.utcnow()
            }
        }
    )

def get_user_github_key(user_id: str):
    """Get the GitHub key for a user from secure storage"""
    # This is a placeholder that would connect to a secure storage service in production
    # For a real implementation, you would use a secure secrets manager
    user = get_user(user_id)
    return user.get("github_key", None) if user.get("github_key_set", False) else None