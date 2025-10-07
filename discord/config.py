"""
Configuration for Discord Bot
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Discord Bot
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# K8s Manager API
K8S_MANAGER_API_URL = os.getenv("K8S_MANAGER_API_URL", "http://localhost:8000")

# MongoDB
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "k8s_manager")

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Validate required config
if not DISCORD_BOT_TOKEN:
    raise ValueError("DISCORD_BOT_TOKEN environment variable is required")
