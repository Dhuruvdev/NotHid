import discord
from discord import app_commands
import config_loader


def get_owner_id() -> int | None:
    return config_loader.get_owner_id()


def is_owner():
    """
    app_commands.check decorator that restricts a command to the bot owner.
    Owner ID is read from data/config.json. Falls back to the Discord
    application owner if not set.
    """
    async def predicate(interaction: discord.Interaction) -> bool:
        owner_id = config_loader.get_owner_id()
        if owner_id:
            return interaction.user.id == owner_id
        app_info = await interaction.client.application_info()
        return interaction.user.id == app_info.owner.id

    return app_commands.check(predicate)
