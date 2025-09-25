import os
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB")
PROJECTS_COLLECTION = "projects"

client = MongoClient(MONGO_URI)
db = client[MONGO_DB]

def get_projects_collection():
    return db[PROJECTS_COLLECTION]

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

def delete_project(project_id: str):
    return get_projects_collection().delete_one({"_id": ObjectId(project_id)})
