import os
import discord
from discord import app_commands

# Owner ID is read from the "Owns" environment variable at startup.
# Set this in Replit Secrets as: key=Owns  value=<your Discord user ID>
_OWNER_ID: str | None = os.environ.get("Owns")


def get_owner_id() -> int | None:
    return int(_OWNER_ID) if _OWNER_ID else None


def is_owner():
    """
    app_commands.check decorator that restricts a command to the bot owner.
    Owner is determined by the 'Owns' environment variable (Discord user ID).
    Falls back to the Discord application owner if the env var is not set.
    """
    async def predicate(interaction: discord.Interaction) -> bool:
        if _OWNER_ID:
            return interaction.user.id == int(_OWNER_ID)
        # Fallback: check Discord application owner
        app_info = await interaction.client.application_info()
        return interaction.user.id == app_info.owner.id

    return app_commands.check(predicate)
