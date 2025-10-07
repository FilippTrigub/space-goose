"""
Authentication Cog
Handles user registration and linking
"""

from datetime import datetime
import discord
from discord import app_commands
from discord.ext import commands
import logging

from services import mongodb_service
from utils.embeds import create_success_embed, create_error_embed, create_info_embed

logger = logging.getLogger(__name__)


class AuthCog(commands.Cog):
    """Commands for user authentication and registration"""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="register", description="Link your Discord account to K8s Manager user"
    )
    async def register(self, interaction: discord.Interaction, user_id: str, blackbox_api_key: str):
        """Register Discord user with K8s Manager user ID"""
        try:
            # Check if user exists in MongoDB
            user = mongodb_service.get_user_info(user_id)
            if not user:
                embed = create_error_embed(
                    "User Not Found",
                    f"User '{user_id}' not found in K8s Manager. Contact admin.",
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Check if already registered
            existing = mongodb_service.get_user_by_discord_id(str(interaction.user.id))
            if existing:
                embed = create_error_embed(
                    "Already Registered",
                    f"You're already registered as '{existing['user_id']}'.\n"
                    f"Use `/unregister` first to link a different account.",
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Check if user has API key configured
            if not user.get("blackbox_api_key_plaintext"):
                embed = create_error_embed(
                    "No API Key",
                    f"User '{user_id}' has no API key configured.\n"
                    f"Please configure an API key first.",
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            if user.get("blackbox_api_key_plaintext") != blackbox_api_key:
                embed = create_error_embed(
                    "API Key incorrect.",
                    f"Please provide the correct API key.",
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            

            # Link Discord ID to user
            mongodb_service.link_discord_user(user_id, str(interaction.user.id))

            embed = create_success_embed(
                "Registration Successful",
                f"Linked to user **{user_id}** ({user.get('name', 'Unknown')})\n\n"
                f"You can now use bot commands to manage projects and sessions.",
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

            logger.info(
                f"Discord user {interaction.user.id} registered as K8s user {user_id}"
            )

        except Exception as e:
            logger.error(f"Registration error: {e}", exc_info=True)
            embed = create_error_embed("Registration Failed", str(e))
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="whoami", description="Show your linked K8s Manager user info"
    )
    async def whoami(self, interaction: discord.Interaction):
        """Show current user info"""
        try:
            user = mongodb_service.get_user_by_discord_id(str(interaction.user.id))

            if not user:
                embed = create_error_embed(
                    "Not Registered",
                    "You're not registered yet.\n\nUse `/register <user_id>` to link your account.",
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            has_api_key = (
                "✅ Yes" if user.get("blackbox_api_key_plaintext") else "❌ No"
            )

            embed = create_info_embed(
                "Your K8s Manager Account",
                f"**User ID:** {user['user_id']}\n"
                f"**Name:** {user.get('name', 'Unknown')}\n"
                f"**API Key:** {has_api_key}\n"
                f"**Discord ID:** {interaction.user.id}",
            )

            if user.get("created_at"):
                embed.add_field(
                    name="Account Created",
                    value=f"{user['created_at']}",
                    inline=False,
                )

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f"Whoami error: {e}", exc_info=True)
            embed = create_error_embed("Error", str(e))
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="unregister", description="Unlink your Discord account")
    async def unregister(self, interaction: discord.Interaction):
        """Unregister Discord user"""
        try:
            user = mongodb_service.get_user_by_discord_id(str(interaction.user.id))

            if not user:
                embed = create_error_embed("Not Registered", "You're not registered.")
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Unlink
            mongodb_service.unlink_discord_user(str(interaction.user.id))

            embed = create_success_embed(
                "Unregistered",
                f"Your Discord account has been unlinked from K8s Manager user '{user['user_id']}'.",
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

            logger.info(
                f"Discord user {interaction.user.id} unregistered from K8s user {user['user_id']}"
            )

        except Exception as e:
            logger.error(f"Unregister error: {e}", exc_info=True)
            embed = create_error_embed("Error", str(e))
            await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    """Load the cog"""
    await bot.add_cog(AuthCog(bot))
