"""
K8s Manager API Client
Handles all HTTP requests to the K8s Manager API
"""
import aiohttp
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class K8sManagerClient:
    """Client for K8s Manager API"""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.timeout = aiohttp.ClientTimeout(total=150)  # 150s for activation (up to 120s)

    def _headers(self, api_key: str) -> Dict[str, str]:
        """Generate headers with API key"""
        return {
            "X-API-Key": api_key,
            "Content-Type": "application/json",
        }

    async def get_projects(self, api_key: str) -> list:
        """Get all projects for user"""
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.get(
                f"{self.base_url}/projects", headers=self._headers(api_key)
            ) as response:
                response.raise_for_status()
                return await response.json()

    async def create_project(
        self, api_key: str, name: str, repo_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new project"""
        data = {"name": name}
        if repo_url:
            data["repo_url"] = repo_url

        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.post(
                f"{self.base_url}/projects",
                headers=self._headers(api_key),
                json=data,
            ) as response:
                response.raise_for_status()
                return await response.json()

    async def delete_project(self, api_key: str, project_id: str) -> Dict[str, Any]:
        """Delete a project"""
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.delete(
                f"{self.base_url}/projects/{project_id}",
                headers=self._headers(api_key),
            ) as response:
                response.raise_for_status()
                return await response.json()

    async def activate_project(self, api_key: str, project_id: str) -> Dict[str, Any]:
        """Activate a project (may take up to 120s)"""
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.post(
                f"{self.base_url}/projects/{project_id}/activate",
                headers=self._headers(api_key),
            ) as response:
                response.raise_for_status()
                return await response.json()

    async def deactivate_project(self, api_key: str, project_id: str) -> Dict[str, Any]:
        """Deactivate a project"""
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.post(
                f"{self.base_url}/projects/{project_id}/deactivate",
                headers=self._headers(api_key),
            ) as response:
                response.raise_for_status()
                return await response.json()

    async def get_sessions(self, api_key: str, project_id: str) -> Dict[str, Any]:
        """Get all sessions for a project"""
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.get(
                f"{self.base_url}/projects/{project_id}/sessions",
                headers=self._headers(api_key),
            ) as response:
                response.raise_for_status()
                return await response.json()

    async def create_session(
        self, api_key: str, project_id: str, name: str
    ) -> Dict[str, Any]:
        """Create a new session"""
        data = {"name": name}

        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.post(
                f"{self.base_url}/projects/{project_id}/sessions",
                headers=self._headers(api_key),
                json=data,
            ) as response:
                response.raise_for_status()
                return await response.json()

    async def delete_session(
        self, api_key: str, project_id: str, session_id: str
    ) -> Dict[str, Any]:
        """Delete a session"""
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.delete(
                f"{self.base_url}/projects/{project_id}/sessions/{session_id}",
                headers=self._headers(api_key),
            ) as response:
                response.raise_for_status()
                return await response.json()

    async def send_message_sync(
        self, api_key: str, project_id: str, session_id: str, content: str
    ) -> Dict[str, Any]:
        """Send message to session (fire-and-forget, non-streaming)"""
        data = {"session_id": session_id, "content": content}

        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.post(
                f"{self.base_url}/projects/{project_id}/messages/send",
                headers=self._headers(api_key),
                json=data,
            ) as response:
                response.raise_for_status()
                return await response.json()

    async def send_message_streaming(
        self, api_key: str, project_id: str, session_id: str, content: str
    ):
        """Send message to session and stream the response (yields chunks)"""
        data = {"session_id": session_id, "content": content}

        headers = self._headers(api_key)
        headers["Accept"] = "text/event-stream"

        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.post(
                f"{self.base_url}/projects/{project_id}/messages",
                headers=headers,
                json=data,
            ) as response:
                response.raise_for_status()

                # Stream SSE chunks
                async for line in response.content:
                    decoded_line = line.decode('utf-8').strip()

                    # SSE format: "data: {json}"
                    if decoded_line.startswith("data: "):
                        json_str = decoded_line[6:]  # Remove "data: " prefix
                        if json_str.strip():
                            try:
                                import json
                                data = json.loads(json_str)
                                yield data
                            except json.JSONDecodeError:
                                # Skip malformed JSON
                                continue
