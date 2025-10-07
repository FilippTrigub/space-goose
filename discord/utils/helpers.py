"""
Helper utility functions
"""
from typing import List


def split_message(text: str, max_length: int = 2000) -> List[str]:
    """
    Split a message into chunks that fit Discord's character limit.

    Args:
        text: The text to split
        max_length: Maximum length per chunk (default 2000 for Discord)

    Returns:
        List of text chunks
    """
    if len(text) <= max_length:
        return [text]

    chunks = []
    current_chunk = ""

    # Split by lines first to avoid breaking mid-line
    lines = text.split("\n")

    for line in lines:
        # If single line is longer than max_length, force split it
        if len(line) > max_length:
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = ""

            # Split long line into chunks
            for i in range(0, len(line), max_length):
                chunks.append(line[i : i + max_length])
            continue

        # Check if adding this line would exceed limit
        if len(current_chunk) + len(line) + 1 > max_length:
            chunks.append(current_chunk)
            current_chunk = line
        else:
            if current_chunk:
                current_chunk += "\n" + line
            else:
                current_chunk = line

    # Add remaining chunk
    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def format_error_message(error: Exception) -> str:
    """
    Format an error message for Discord display.

    Args:
        error: The exception to format

    Returns:
        Formatted error string
    """
    error_msg = str(error)

    # Handle aiohttp errors
    if "401" in error_msg or "Unauthorized" in error_msg:
        return "❌ Authentication failed (invalid API key)"
    elif "404" in error_msg or "Not Found" in error_msg:
        return "❌ Resource not found"
    elif "400" in error_msg or "Bad Request" in error_msg:
        return f"❌ Bad request: {error_msg}"
    elif "500" in error_msg or "Internal Server Error" in error_msg:
        return f"❌ API error: {error_msg}"
    elif "timeout" in error_msg.lower():
        return "⏱️ Request timed out (>150s)"
    else:
        return f"❌ Error: {error_msg}"
