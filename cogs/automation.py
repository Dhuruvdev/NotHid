import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional

import storage


class AutomationCog(commands.Cog, name="Automation"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ── Auto Role ────────────────────────────────────────────────────────────

    autorole_group = app_commands.Group(name="autorole", description="Configure automatic role assignment on join.")

    @autorole_group.command(name="set", description="Set the role automatically assigned to new members.")
    @app_commands.describe(role="The role to auto-assign")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def autorole_set(self, interaction: discord.Interaction, role: discord.Role):
        if role >= interaction.guild.me.top_role:
            await interaction.response.send_message("❌ I cannot assign a role higher than my own.", ephemeral=True)
            return
        storage.set_server_config(interaction.guild_id, autorole=str(role.id))
        embed = discord.Embed(
            title="✅ Auto Role Set",
            description=f"New members will automatically receive {role.mention} on join.",
            color=discord.Color.green(),
        )
        await interaction.response.send_message(embed=embed)

    @autorole_group.command(name="remove", description="Remove the auto-role configuration.")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def autorole_remove(self, interaction: discord.Interaction):
        storage.set_server_config(interaction.guild_id, autorole=None)
        embed = discord.Embed(
            title="✅ Auto Role Removed",
            description="Auto role assignment has been disabled.",
            color=discord.Color.green(),
        )
        await interaction.response.send_message(embed=embed)

    @autorole_group.command(name="status", description="Check the current auto-role configuration.")
    async def autorole_status(self, interaction: discord.Interaction):
        cfg = storage.get_server_config(interaction.guild_id)
        role_id = cfg.get("autorole")
        if role_id:
            role = interaction.guild.get_role(int(role_id))
            desc = f"Auto role is set to {role.mention if role else '`Deleted role`'}."
        else:
            desc = "No auto role is configured. Use `/autorole set` to configure one."
        embed = discord.Embed(title="Auto Role Status", description=desc, color=discord.Color.blurple())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ── Auto Kick ────────────────────────────────────────────────────────────

    autokick_group = app_commands.Group(name="autokick", description="Configure automatic kick for inactive members.")

    @autokick_group.command(name="set", description="Kick members inactive for more than N days.")
    @app_commands.describe(days="Inactivity threshold in days (0 to disable)")
    @app_commands.checks.has_permissions(kick_members=True)
    async def autokick_set(self, interaction: discord.Interaction, days: int):
        if days <= 0:
            storage.set_server_config(interaction.guild_id, autokick_days=None)
            embed = discord.Embed(title="✅ Auto-Kick Disabled", description="Inactive member auto-kick has been turned off.", color=discord.Color.green())
        else:
            storage.set_server_config(interaction.guild_id, autokick_days=days)
            embed = discord.Embed(
                title="✅ Auto-Kick Configured",
                description=f"Members inactive for **{days} days** will be eligible for auto-kick.\n\n*Note: Run `/inactive` to review and kick manually.*",
                color=discord.Color.orange(),
            )
        await interaction.response.send_message(embed=embed)

    # ── Auto Warn ────────────────────────────────────────────────────────────

    autowarn_group = app_commands.Group(name="autowarn", description="Configure automatic warnings for spam.")

    @autowarn_group.command(name="spam", description="Toggle automatic warnings for spam detection.")
    @app_commands.describe(enabled="Turn on or off")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def autowarn_spam(self, interaction: discord.Interaction, enabled: bool):
        storage.set_server_config(interaction.guild_id, autowarn_spam=enabled)
        state = "enabled ✅" if enabled else "disabled ❌"
        embed = discord.Embed(
            title="Auto-Warn Spam",
            description=f"Automatic spam warnings are now **{state}**.",
            color=discord.Color.green() if enabled else discord.Color.red(),
        )
        await interaction.response.send_message(embed=embed)

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("❌ You lack the required permissions.", ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ Error: `{error}`", ephemeral=True)


async def setup(bot: commands.Bot):
    cog = AutomationCog(bot)
    cog.bot = bot
    bot.tree.add_command(cog.autorole_group)
    bot.tree.add_command(cog.autokick_group)
    bot.tree.add_command(cog.autowarn_group)
    await bot.add_cog(cog)
