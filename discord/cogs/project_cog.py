"""
Project Management Cog
Handles project CRUD operations
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
    create_projects_embed,
    create_project_info_embed,
)
from utils.helpers import format_error_message
import config

logger = logging.getLogger(__name__)


class ProjectCog(commands.Cog):
    """Commands for project management"""

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

    @app_commands.command(
        name="projects-list", description="List all your projects"
    )
    async def projects_list(self, interaction: discord.Interaction):
        """List all projects"""
        try:
            user, api_key = self._get_user_and_api_key(str(interaction.user.id))

            await interaction.response.defer()

            projects = await self.api_client.get_projects(api_key)

            embed = create_projects_embed(projects)
            await interaction.followup.send(embed=embed)

        except ValueError as e:
            embed = create_error_embed("Error", str(e))
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"List projects error: {e}", exc_info=True)
            embed = create_error_embed("Error", format_error_message(e))
            try:
                await interaction.response.send_message(embed=embed, ephemeral=True)
            except:
                await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(
        name="projects-create", description="Create a new project"
    )
    async def projects_create(
        self,
        interaction: discord.Interaction,
        name: str,
        repo_url: str = None,
    ):
        """Create a new project"""
        try:
            user, api_key = self._get_user_and_api_key(str(interaction.user.id))

            await interaction.response.defer()

            result = await self.api_client.create_project(api_key, name, repo_url)

            embed = create_success_embed(
                "Project Created",
                f"Project **{name}** created successfully!\n\n"
                f"Project ID: `{result['project_id']}`\n"
                f"The project is now active and ready to use.",
            )

            if repo_url:
                embed.add_field(name="Repository", value=repo_url, inline=False)

            await interaction.followup.send(embed=embed)

            logger.info(
                f"User {user['user_id']} created project {name} ({result['project_id']})"
            )

        except ValueError as e:
            embed = create_error_embed("Error", str(e))
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"Create project error: {e}", exc_info=True)
            embed = create_error_embed("Error", format_error_message(e))
            try:
                await interaction.response.send_message(embed=embed, ephemeral=True)
            except:
                await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(
        name="projects-delete", description="Delete a project"
    )
    async def projects_delete(
        self, interaction: discord.Interaction, project_name: str
    ):
        """Delete a project"""
        try:
            user, api_key = self._get_user_and_api_key(str(interaction.user.id))

            await interaction.response.defer()

            # Find project by name
            projects = await self.api_client.get_projects(api_key)
            project = self._find_project_by_name(projects, project_name)

            # Delete project
            await self.api_client.delete_project(api_key, project["id"])

            embed = create_success_embed(
                "Project Deleted", f"Project **{project_name}** has been deleted."
            )
            await interaction.followup.send(embed=embed)

            logger.info(
                f"User {user['user_id']} deleted project {project_name} ({project['id']})"
            )

        except ValueError as e:
            embed = create_error_embed("Error", str(e))
            try:
                await interaction.response.send_message(embed=embed, ephemeral=True)
            except:
                await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"Delete project error: {e}", exc_info=True)
            embed = create_error_embed("Error", format_error_message(e))
            try:
                await interaction.response.send_message(embed=embed, ephemeral=True)
            except:
                await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(
        name="projects-activate",
        description="Activate a project (may take up to 120 seconds)",
    )
    async def projects_activate(
        self, interaction: discord.Interaction, project_name: str
    ):
        """Activate a project"""
        try:
            user, api_key = self._get_user_and_api_key(str(interaction.user.id))

            await interaction.response.defer()

            # Find project by name
            projects = await self.api_client.get_projects(api_key)
            project = self._find_project_by_name(projects, project_name)

            # Activate project (may take up to 120s)
            result = await self.api_client.activate_project(api_key, project["id"])

            endpoint = result.get("endpoint", "N/A")

            embed = create_success_embed(
                "Project Activated",
                f"Project **{project_name}** is now active!\n\n"
                f"Endpoint: `{endpoint}`",
            )
            await interaction.followup.send(embed=embed)

            logger.info(
                f"User {user['user_id']} activated project {project_name} ({project['id']})"
            )

        except ValueError as e:
            embed = create_error_embed("Error", str(e))
            try:
                await interaction.response.send_message(embed=embed, ephemeral=True)
            except:
                await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"Activate project error: {e}", exc_info=True)
            embed = create_error_embed("Error", format_error_message(e))
            try:
                await interaction.response.send_message(embed=embed, ephemeral=True)
            except:
                await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(
        name="projects-deactivate", description="Deactivate a project"
    )
    async def projects_deactivate(
        self, interaction: discord.Interaction, project_name: str
    ):
        """Deactivate a project"""
        try:
            user, api_key = self._get_user_and_api_key(str(interaction.user.id))

            await interaction.response.defer()

            # Find project by name
            projects = await self.api_client.get_projects(api_key)
            project = self._find_project_by_name(projects, project_name)

            # Deactivate project
            await self.api_client.deactivate_project(api_key, project["id"])

            embed = create_success_embed(
                "Project Deactivated",
                f"Project **{project_name}** has been deactivated.",
            )
            await interaction.followup.send(embed=embed)

            logger.info(
                f"User {user['user_id']} deactivated project {project_name} ({project['id']})"
            )

        except ValueError as e:
            embed = create_error_embed("Error", str(e))
            try:
                await interaction.response.send_message(embed=embed, ephemeral=True)
            except:
                await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"Deactivate project error: {e}", exc_info=True)
            embed = create_error_embed("Error", format_error_message(e))
            try:
                await interaction.response.send_message(embed=embed, ephemeral=True)
            except:
                await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(
        name="projects-info", description="Get detailed project information"
    )
    async def projects_info(
        self, interaction: discord.Interaction, project_name: str
    ):
        """Get project info"""
        try:
            user, api_key = self._get_user_and_api_key(str(interaction.user.id))

            await interaction.response.defer()

            # Find project by name
            projects = await self.api_client.get_projects(api_key)
            project = self._find_project_by_name(projects, project_name)

            embed = create_project_info_embed(project)
            await interaction.followup.send(embed=embed)

        except ValueError as e:
            embed = create_error_embed("Error", str(e))
            try:
                await interaction.response.send_message(embed=embed, ephemeral=True)
            except:
                await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"Project info error: {e}", exc_info=True)
            embed = create_error_embed("Error", format_error_message(e))
            try:
                await interaction.response.send_message(embed=embed, ephemeral=True)
            except:
                await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    """Load the cog"""
    await bot.add_cog(ProjectCog(bot))
