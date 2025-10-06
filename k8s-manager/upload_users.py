from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

from services import mongodb_service

set_users = [
    {"id": "user1", "name": "User 1"},
    {"id": "user2", "name": "User 2"},
    {"id": "user3", "name": "FILIPP TEST USER"},
]

user_collection = mongodb_service.get_users_collection()
existing_users = user_collection.find({})
existing_user_ids = [str(user["user_id"]) for user in existing_users]
print(existing_user_ids)

for user in set_users:
    if user["id"] not in existing_user_ids:
        user_data = {
            "user_id": user["id"],
            "name": user["name"],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "api_key": ""
        }
        user_collection.insert_one(user_data)