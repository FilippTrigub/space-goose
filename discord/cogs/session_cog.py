"""
Session Management Cog
Handles session CRUD operations
"""
import discord
from discord import app_commands
from discord.ext import commands
import logging

from services import mongodb_service
from services.api_client import K8sManagerClient
from utils.embeds import (
    create_success_embed,
    create_error_embed,
    create_sessions_embed,
)
from utils.helpers import format_error_message
import config

logger = logging.getLogger(__name__)


class SessionCog(commands.Cog):
    """Commands for session management"""

    def __init__(self, bot):
        self.bot = bot
        self.api_client = K8sManagerClient(config.K8S_MANAGER_API_URL)

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
            (s for s in sessions if s.get("name") == session_name or s["session_id"] == session_name),
            None,
        )
        if not session:
            raise ValueError(f"Session '{session_name}' not found")
        return session

    @app_commands.command(
        name="sessions-list", description="List all sessions in a project"
    )
    async def sessions_list(
        self, interaction: discord.Interaction, project_name: str
    ):
        """List all sessions"""
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

            # Get sessions
            result = await self.api_client.get_sessions(api_key, project["id"])
            sessions = result.get("sessions", [])

            embed = create_sessions_embed(project_name, sessions)
            await interaction.followup.send(embed=embed)

        except ValueError as e:
            embed = create_error_embed("Error", str(e))
            try:
                await interaction.response.send_message(embed=embed, ephemeral=True)
            except:
                await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"List sessions error: {e}", exc_info=True)
            embed = create_error_embed("Error", format_error_message(e))
            try:
                await interaction.response.send_message(embed=embed, ephemeral=True)
            except:
                await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(
        name="sessions-create", description="Create a new session"
    )
    async def sessions_create(
        self,
        interaction: discord.Interaction,
        project_name: str,
        session_name: str,
    ):
        """Create a new session"""
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

            # Create session
            result = await self.api_client.create_session(
                api_key, project["id"], session_name
            )

            session_id = result["session"]["session_id"]

            embed = create_success_embed(
                "Session Created",
                f"Session **{session_name}** created in project **{project_name}**!\n\n"
                f"Session ID: `{session_id}`\n\n"
                f"You can now send messages using:\n"
                f"`/ask-session {project_name} {session_name} <message>`",
            )
            await interaction.followup.send(embed=embed)

            logger.info(
                f"User {user['user_id']} created session {session_name} in project {project_name}"
            )

        except ValueError as e:
            embed = create_error_embed("Error", str(e))
            try:
                await interaction.response.send_message(embed=embed, ephemeral=True)
            except:
                await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"Create session error: {e}", exc_info=True)
            embed = create_error_embed("Error", format_error_message(e))
            try:
                await interaction.response.send_message(embed=embed, ephemeral=True)
            except:
                await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(
        name="sessions-delete", description="Delete a session"
    )
    async def sessions_delete(
        self,
        interaction: discord.Interaction,
        project_name: str,
        session_name: str,
    ):
        """Delete a session"""
        try:
            user, api_key = self._get_user_and_api_key(str(interaction.user.id))

            await interaction.response.defer()

            # Find project by name
            projects = await self.api_client.get_projects(api_key)
            project = self._find_project_by_name(projects, project_name)

            # Get sessions to find session by name
            result = await self.api_client.get_sessions(api_key, project["id"])
            sessions = result.get("sessions", [])

            session = self._find_session_by_name(sessions, session_name)

            # Delete session
            await self.api_client.delete_session(
                api_key, project["id"], session["session_id"]
            )

            embed = create_success_embed(
                "Session Deleted",
                f"Session **{session_name}** has been deleted from project **{project_name}**.",
            )
            await interaction.followup.send(embed=embed)

            logger.info(
                f"User {user['user_id']} deleted session {session_name} from project {project_name}"
            )

        except ValueError as e:
            embed = create_error_embed("Error", str(e))
            try:
                await interaction.response.send_message(embed=embed, ephemeral=True)
            except:
                await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"Delete session error: {e}", exc_info=True)
            embed = create_error_embed("Error", format_error_message(e))
            try:
                await interaction.response.send_message(embed=embed, ephemeral=True)
            except:
                await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    """Load the cog"""
    await bot.add_cog(SessionCog(bot))
