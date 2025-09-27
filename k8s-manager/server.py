import asyncio
import sys
from typing import List, Dict, Any, Optional
from fastmcp import FastMCP
from tools import ChatTools, ImageTools, ModelTools
from config import config

# Initialize the MCP server
mcp = FastMCP(
    name="Space Goose MCP Server",
    instructions="MCP server providing access to the the Space Goose API to remotely execute the goose coding agent."
)

@mcp.tool
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
        temperature: Controls randomness (0.0 to 2.0, default: 0.7)
        max_tokens: Maximum tokens to generate (default: 1024)
        stream: Whether to stream the response (default: false)
        
    Returns:
        The generated response text
    """
    return await ChatTools.blackbox_chat(model, messages, temperature, max_tokens, stream)

@mcp.tool
async def blackbox_image(
    prompt: str,
    model: str = "blackboxai/black-forest-labs/flux-pro"
) -> str:
    """
    Generate an image using Blackbox AI.
    
    Args:
        prompt: Description of the image to generate (max 2K characters)
        model: The image model to use (default: flux-pro)
        
    Returns:
        URL of the generated image
    """
    return await ImageTools.blackbox_image(prompt, model)

@mcp.tool
async def blackbox_models(model_type: Optional[str] = None) -> Dict[str, Any]:
    """
    List available Blackbox AI models.
    
    Args:
        model_type: Filter by type ('chat', 'image', 'video', 'speech'). If None, returns all types.
        
    Returns:
        Dictionary containing available models and their information
    """
    return await ModelTools.list_models(model_type)

@mcp.tool
async def test_connection() -> Dict[str, Any]:
    """
    Test the connection to Blackbox AI API by making a simple chat request.
    
    Returns:
        Connection status and API key validity
    """
    try:
        # Test with a simple chat message
        test_messages = [{"role": "user", "content": "Hello, respond with just 'OK'"}]
        response = await ChatTools.blackbox_chat(
            model="blackboxai/openai/gpt-4",
            messages=test_messages,
            temperature=0.1,
            max_tokens=10
        )
        
        return {
            "status": "success",
            "message": "Connection to Blackbox AI API successful",
            "api_key_valid": True,
            "test_response": response
        }
    except Exception as e:
        return {
            "status": "error", 
            "message": f"Connection failed: {str(e)}",
            "api_key_valid": False
        }

def main():
    """Main entry point for the MCP server"""
    try:
        # Validate configuration on startup
        print(f"Starting Blackbox MCP Server...", file=sys.stderr)
        print(f"API Key configured: {'Yes' if config.api_key else 'No'}", file=sys.stderr)
        
        # Run the server with STDIO transport
        mcp.run()
        
    except Exception as e:
        print(f"Failed to start server: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()