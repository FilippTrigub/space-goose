import os
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB")
PROJECTS_COLLECTION = "projects"
USERS_COLLECTION = "users"  # New collection for user data

client = MongoClient(MONGO_URI)
db = client[MONGO_DB]


def get_users_collection():
    return db[USERS_COLLECTION]


def get_user_info(user_id: str):
    return get_users_collection().find_one({"user_id": user_id})


def link_discord_user(user_id: str, discord_user_id: str):
    """Link a Discord user ID to an existing K8s Manager user"""
    return get_users_collection().update_one(
        {"user_id": user_id},
        {"$set": {"discord_user_id": discord_user_id, "updated_at": datetime.utcnow()}},
    )


def get_user_by_discord_id(discord_user_id: str):
    """Get user by Discord ID"""
    return get_users_collection().find_one({"discord_user_id": discord_user_id})


def unlink_discord_user(discord_user_id: str):
    """Remove Discord user link"""
    return get_users_collection().update_one(
        {"discord_user_id": discord_user_id},
        {"$unset": {"discord_user_id": ""}, "$set": {"updated_at": datetime.utcnow()}},
    )
