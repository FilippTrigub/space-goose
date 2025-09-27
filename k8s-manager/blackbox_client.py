import httpx
from typing import Dict, List, Any, Optional
from pydantic import BaseModel
from config import config

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    temperature: float = 0.7
    max_tokens: int = 1024
    stream: bool = False

class ImageRequest(BaseModel):
    model: str = "blackboxai/black-forest-labs/flux-pro"
    messages: List[ChatMessage]

class BlackboxClient:
    def __init__(self):
        self.client = httpx.AsyncClient(
            base_url=config.base_url,
            timeout=config.timeout,
            headers=config.auth_header
        )
    
    async def chat_completion(self, request: ChatRequest) -> Dict[str, Any]:
        """Send a chat completion request to Blackbox API"""
        try:
            response = await self.client.post(
                "/chat/completions",
                json=request.model_dump()
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise Exception("Invalid API key. Check your BLACKBOX_API_KEY environment variable.")
            elif e.response.status_code == 429:
                raise Exception("Rate limit exceeded. Please try again later.")
            else:
                raise Exception(f"API request failed: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            raise Exception(f"Request failed: {str(e)}")
    
    async def generate_image(self, prompt: str, model: str = "blackboxai/black-forest-labs/flux-pro") -> Dict[str, Any]:
        """Generate an image using Blackbox API"""
        request = ImageRequest(
            model=model,
            messages=[ChatMessage(role="user", content=prompt)]
        )
        
        try:
            response = await self.client.post(
                "/chat/completions",
                json=request.model_dump()
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise Exception("Invalid API key. Check your BLACKBOX_API_KEY environment variable.")
            elif e.response.status_code == 429:
                raise Exception("Rate limit exceeded. Please try again later.")
            else:
                raise Exception(f"API request failed: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            raise Exception(f"Image generation failed: {str(e)}")
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()

client = BlackboxClient()