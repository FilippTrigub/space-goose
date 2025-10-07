"""
K8s Manager Discord Bot
Main entry point
"""
import discord
from discord.ext import commands
import logging
import asyncio

import config

# Set up logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class K8sManagerBot(commands.Bot):
    """K8s Manager Discord Bot"""

    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True

        super().__init__(
            command_prefix="!",  # Prefix for text commands (not used for slash commands)
            intents=intents,
            help_command=None,  # Disable default help command
        )

    async def setup_hook(self):
        """Load cogs and sync commands"""
        logger.info("Loading cogs...")

        # Load all cogs
        cogs = [
            "cogs.auth_cog",
            "cogs.project_cog",
            "cogs.session_cog",
            "cogs.messaging_cog",
        ]

        for cog in cogs:
            try:
                await self.load_extension(cog)
                logger.info(f"Loaded {cog}")
            except Exception as e:
                logger.error(f"Failed to load {cog}: {e}", exc_info=True)

        # Sync slash commands with Discord
        logger.info("Syncing commands with Discord...")
        try:
            synced = await self.tree.sync()
            logger.info(f"Synced {len(synced)} commands")
        except Exception as e:
            logger.error(f"Failed to sync commands: {e}", exc_info=True)

    async def on_ready(self):
        """Called when bot is ready"""
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        logger.info(f"Connected to {len(self.guilds)} guilds")
        logger.info("Bot is ready!")

        # Set bot presence
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching, name="K8s Manager"
            )
        )

    async def on_command_error(self, ctx, error):
        """Handle command errors"""
        if isinstance(error, commands.CommandNotFound):
            return  # Ignore unknown commands

        logger.error(f"Command error: {error}", exc_info=True)

    async def on_application_command_error(
        self, interaction: discord.Interaction, error: discord.app_commands.AppCommandError
    ):
        """Handle application command errors"""
        logger.error(f"Application command error: {error}", exc_info=True)

        if not interaction.response.is_done():
            await interaction.response.send_message(
                f"❌ An error occurred: {str(error)}", ephemeral=True
            )
        else:
            await interaction.followup.send(
                f"❌ An error occurred: {str(error)}", ephemeral=True
            )


async def main():
    """Main function"""
    bot = K8sManagerBot()

    try:
        await bot.start(config.DISCORD_BOT_TOKEN)
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
        await bot.close()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        await bot.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped")
