"""
Messaging Cog
Handles AI agent interactions
"""

import discord
from discord import app_commands
from discord.ext import commands
import logging
from datetime import datetime
import asyncio

from services import mongodb_service
from services.api_client import K8sManagerClient
from utils.embeds import create_success_embed, create_error_embed
from utils.helpers import format_error_message, split_message
import config

logger = logging.getLogger(__name__)


class MessagingCog(commands.Cog):
    """Commands for sending messages to AI agent"""

    def __init__(self, bot):
        self.bot = bot
        self.api_client = K8sManagerClient(config.K8S_MANAGER_API_URL)
        self.max_chunk_length = 1900  # Discord message limit
        self.edit_rate_limit = 3.0  # Edit every 3 seconds

    def _get_user_and_api_key(self, discord_user_id: str):
        """Helper to get user and API key"""
        user = mongodb_service.get_user_by_discord_id(discord_user_id)
        if not user:
            raise ValueError("Not registered. Use `/register <user_id>` first.")

        api_key = user.get("blackbox_api_key_plaintext")
        if not api_key:
            raise ValueError("Your user has no API key configured.")

        return user, api_key

    def _find_project_by_name(self, projects: list, project_name: str):
        """Helper to find project by name"""
        project = next((p for p in projects if p["name"] == project_name), None)
        if not project:
            raise ValueError(f"Project '{project_name}' not found")
        return project

    def _find_session_by_name(self, sessions: list, session_name: str):
        """Helper to find session by name"""
        session = next(
            (
                s
                for s in sessions
                if s.get("name") == session_name or s["session_id"] == session_name
            ),
            None,
        )
        if not session:
            raise ValueError(f"Session '{session_name}' not found")
        return session

    async def _stream_to_discord(
        self,
        message,
        api_key: str,
        project_id: str,
        session_id: str,
        prompt: str,
        session_name: str,
    ):
        """Stream response from API to Discord with buffering"""
        buffer = ""
        last_update = 0
        header = f"🤖 **Session: {session_name}**\n\n"
        limit_reached = False

        try:
            async for chunk in self.api_client.send_message_streaming(
                api_key, project_id, session_id, prompt
            ):
                # Handle errors in stream
                if chunk.get("error"):
                    error_msg = f"\n\n❌ **Error:** {chunk['error']}"
                    await message.edit(content=header + buffer + error_msg)
                    return

                # Extract content from SSE chunk
                content = chunk.get("content", "")
                if not content:
                    # Check for completion signal
                    if chunk.get("type") == "completion":
                        break
                    continue

                buffer += content.get("content", "")

                # Check if buffer exceeds Discord limit
                if len(header + buffer) >= self.max_chunk_length:
                    limit_reached = True
                    # Truncate buffer
                    buffer = buffer[
                        : self.max_chunk_length - len(header) - 200
                    ]  # Leave room for limit message
                    limit_msg = "\n\n⚠️ **Response truncated** - Use session commands to view full content"
                    await message.edit(content=header + buffer + limit_msg)
                    return

                # Rate-limit message edits (edit every 3 seconds)
                current_time = asyncio.get_event_loop().time()
                if current_time - last_update >= self.edit_rate_limit:
                    await message.edit(content=header + buffer)
                    last_update = current_time

            # Final update with complete response
            if not limit_reached and buffer:
                await message.edit(content=header + buffer)

        except Exception as e:
            logger.error(f"Streaming error: {e}", exc_info=True)
            error_msg = f"\n\n❌ **Error during streaming:** {format_error_message(e)}"
            try:
                await message.edit(content=header + buffer + error_msg)
            except:
                await message.channel.send(error_msg)

    @app_commands.command(
        name="ask", description="Create a new session and send a message to AI"
    )
    async def ask(
        self, interaction: discord.Interaction, project_name: str, message: str
    ):
        """Create new session and send message with streaming response"""
        try:
            user, api_key = self._get_user_and_api_key(str(interaction.user.id))

            await interaction.response.defer()

            # Find project by name
            projects = await self.api_client.get_projects(api_key)
            project = self._find_project_by_name(projects, project_name)

            # Check if project is active
            if project["status"] != "active":
                embed = create_error_embed(
                    "Project Inactive",
                    f"Project '{project_name}' is not active.\n"
                    f"Use `/projects-activate {project_name}` first.",
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # Create new session with timestamp
            session_name = f"chat-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            session_result = await self.api_client.create_session(
                api_key, project["id"], session_name
            )
            session_id = session_result["session"]["session_id"]

            logger.info(
                f"User {user['user_id']} created session {session_name} in project {project_name}"
            )

            # Send initial message placeholder
            initial_msg = await interaction.followup.send(
                f"🤖 **Session: {session_name}**\n\n_Thinking..._"
            )

            # Stream the response
            await self._stream_to_discord(
                initial_msg, api_key, project["id"], session_id, message, session_name
            )

            logger.info(
                f"User {user['user_id']} sent message to new session {session_name} in project {project_name}"
            )

        except ValueError as e:
            embed = create_error_embed("Error", str(e))
            try:
                await interaction.response.send_message(embed=embed, ephemeral=True)
            except:
                await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"Ask error: {e}", exc_info=True)
            embed = create_error_embed("Error", format_error_message(e))
            try:
                await interaction.response.send_message(embed=embed, ephemeral=True)
            except:
                await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(
        name="ask-session", description="Send a message to an existing session"
    )
    async def ask_session(
        self,
        interaction: discord.Interaction,
        project_name: str,
        session_name: str,
        message: str,
    ):
        """Send message to existing session with streaming response"""
        try:
            user, api_key = self._get_user_and_api_key(str(interaction.user.id))

            await interaction.response.defer()

            # Find project by name
            projects = await self.api_client.get_projects(api_key)
            project = self._find_project_by_name(projects, project_name)

            # Check if project is active
            if project["status"] != "active":
                embed = create_error_embed(
                    "Project Inactive",
                    f"Project '{project_name}' is not active.\n"
                    f"Use `/projects-activate {project_name}` first.",
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # Get sessions to find session by name
            sessions_result = await self.api_client.get_sessions(api_key, project["id"])
            sessions = sessions_result.get("sessions", [])

            session = self._find_session_by_name(sessions, session_name)
            session_id = session["session_id"]

            # Send initial message placeholder
            initial_msg = await interaction.followup.send(
                f"🤖 **Session: {session_name}**\n\n_Thinking..._"
            )

            # Stream the response
            await self._stream_to_discord(
                initial_msg, api_key, project["id"], session_id, message, session_name
            )

            logger.info(
                f"User {user['user_id']} sent message to session {session_name} in project {project_name}"
            )

        except ValueError as e:
            embed = create_error_embed("Error", str(e))
            try:
                await interaction.response.send_message(embed=embed, ephemeral=True)
            except:
                await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"Ask session error: {e}", exc_info=True)
            embed = create_error_embed("Error", format_error_message(e))
            try:
                await interaction.response.send_message(embed=embed, ephemeral=True)
            except:
                await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    """Load the cog"""
    await bot.add_cog(MessagingCog(bot))
