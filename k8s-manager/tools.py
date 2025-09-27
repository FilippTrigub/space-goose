from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from blackbox_client import client, ChatMessage, ChatRequest

class ChatTools:
    @staticmethod
    async def blackbox_chat(
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1024,
        stream: bool = False
    ) -> str:
        """
        Send a chat completion request to Blackbox AI.
        
        Args:
            model: The model ID to use (e.g., 'blackboxai/openai/gpt-4')
            messages: List of message objects with 'role' and 'content' keys
            temperature: Controls randomness (0.0 to 2.0)
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response
            
        Returns:
            The generated response text
        """
        try:
            # Convert messages to ChatMessage objects
            chat_messages = [ChatMessage(role=msg["role"], content=msg["content"]) for msg in messages]
            
            request = ChatRequest(
                model=model,
                messages=chat_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=stream
            )
            
            response = await client.chat_completion(request)
            
            # Extract the response content
            if "choices" in response and len(response["choices"]) > 0:
                return response["choices"][0]["message"]["content"]
            else:
                raise Exception("No response content received from API")
                
        except Exception as e:
            raise Exception(f"Chat completion failed: {str(e)}")

class ImageTools:
    @staticmethod
    async def blackbox_image(
        prompt: str,
        model: str = "blackboxai/black-forest-labs/flux-pro"
    ) -> str:
        """
        Generate an image using Blackbox AI.
        
        Args:
            prompt: Description of the image to generate (max 2K characters)
            model: The image model to use
            
        Returns:
            URL of the generated image
        """
        try:
            if len(prompt) > 2000:
                raise Exception("Prompt must be 2000 characters or less")
            
            response = await client.generate_image(prompt, model)
            
            # Extract the image URL from response
            if "choices" in response and len(response["choices"]) > 0:
                content = response["choices"][0]["message"]["content"]
                # The response should contain the image URL
                return content
            else:
                raise Exception("No image URL received from API")
                
        except Exception as e:
            raise Exception(f"Image generation failed: {str(e)}")

class ModelTools:
    @staticmethod
    async def list_models(model_type: Optional[str] = None) -> Dict[str, Any]:
        """
        List available Blackbox AI models.
        
        Args:
            model_type: Filter by type (chat, image, video, speech)
            
        Returns:
            Dictionary containing available models and their information
        """
        # For hackathon, return a static list of popular models
        # In production, this could fetch from an actual models endpoint
        
        models = {
            "chat": [
                {
                    "id": "blackboxai/openai/gpt-4",
                    "name": "GPT-4",
                    "provider": "OpenAI",
                    "context_length": 8192
                },
                {
                    "id": "blackboxai/anthropic/claude-3-sonnet",
                    "name": "Claude 3 Sonnet",
                    "provider": "Anthropic",
                    "context_length": 200000
                },
                {
                    "id": "blackboxai/mistral/mistral-small",
                    "name": "Mistral Small",
                    "provider": "Mistral",
                    "context_length": 32768
                }
            ],
            "image": [
                {
                    "id": "blackboxai/black-forest-labs/flux-pro",
                    "name": "Flux Pro",
                    "provider": "Black Forest Labs",
                    "max_prompt_length": 2000
                },
                {
                    "id": "blackboxai/stability-ai/stable-diffusion",
                    "name": "Stable Diffusion",
                    "provider": "Stability AI",
                    "max_prompt_length": 2000
                }
            ]
        }
        
        if model_type:
            return {model_type: models.get(model_type, [])}
        
        return models