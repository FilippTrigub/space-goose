import os
from typing import Optional
from dotenv import load_dotenv

class Config:
    def __init__(self):
        self.api_key = self._get_api_key()
        self.base_url = "https://api.blackbox.ai"
        self.timeout = 120.0  # Increased timeout for slow BlackBox API
        
    def _get_api_key(self) -> str:
        load_dotenv()
        api_key = os.getenv("BLACKBOX_API_KEY")
        if not api_key:
            raise ValueError(
                "BLACKBOX_API_KEY environment variable is required. "
                "Get your API key from the BLACKBOX dashboard."
            )
        return api_key
    
    @property
    def auth_header(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}

config = Config()