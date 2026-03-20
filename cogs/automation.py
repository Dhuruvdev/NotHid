import discord
from discord.ext import commands
from discord import app_commands

import storage
import emojis_loader as E

WHITE = discord.Color.from_rgb(255, 255, 255)


def _parse_bool(value: str):
    if value.lower() in ("on", "true", "yes", "enable", "1"):
        return True
    if value.lower() in ("off", "false", "no", "disable", "0"):
        return False
    return None


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
            await interaction.response.send_message(f"{E.get('error', '❌')} I cannot assign a role higher than my own.", ephemeral=True)
            return
        storage.set_server_config(interaction.guild_id, autorole=str(role.id))
        embed = discord.Embed(
            description=f"{E.get('success', '✅')} Auto role set — new members will receive {role.mention} on join.",
            color=discord.Color.green(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @autorole_group.command(name="remove", description="Remove the auto-role configuration.")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def autorole_remove(self, interaction: discord.Interaction):
        storage.set_server_config(interaction.guild_id, autorole=None)
        embed = discord.Embed(
            description=f"{E.get('success', '✅')} Auto role removed — role assignment on join is disabled.",
            color=discord.Color.green(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @autorole_group.command(name="status", description="Check the current auto-role configuration.")
    async def autorole_status(self, interaction: discord.Interaction):
        cfg = storage.get_server_config(interaction.guild_id)
        role_id = cfg.get("autorole")
        if role_id:
            role = interaction.guild.get_role(int(role_id))
            desc = f"{E.get('success', '✅')} Auto role is set to {role.mention if role else '`Deleted role`'}."
        else:
            desc = f"{E.get('info', 'ℹ️')} No auto role configured. Use `>autoroleset @role` to configure one."
        embed = discord.Embed(description=desc, color=WHITE)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ── Auto Kick ────────────────────────────────────────────────────────────

    autokick_group = app_commands.Group(name="autokick", description="Configure automatic kick for inactive members.")

    @autokick_group.command(name="set", description="Kick members inactive for more than N days.")
    @app_commands.describe(days="Inactivity threshold in days (0 to disable)")
    @app_commands.checks.has_permissions(kick_members=True)
    async def autokick_set(self, interaction: discord.Interaction, days: int):
        if days <= 0:
            storage.set_server_config(interaction.guild_id, autokick_days=None)
            embed = discord.Embed(description=f"{E.get('success', '✅')} Auto-kick disabled.", color=discord.Color.green())
        else:
            storage.set_server_config(interaction.guild_id, autokick_days=days)
            embed = discord.Embed(
                description=f"{E.get('success', '✅')} Auto-kick set — members inactive for **{days} days** are eligible. Run `>inactive` to review.",
                color=discord.Color.orange(),
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ── Auto Warn ────────────────────────────────────────────────────────────

    autowarn_group = app_commands.Group(name="autowarn", description="Configure automatic warnings for spam.")

    @autowarn_group.command(name="spam", description="Toggle automatic warnings for spam detection.")
    @app_commands.describe(enabled="Turn on or off")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def autowarn_spam(self, interaction: discord.Interaction, enabled: bool):
        storage.set_server_config(interaction.guild_id, autowarn_spam=enabled)
        icon = E.get("success", "✅") if enabled else E.get("error", "❌")
        state = "enabled" if enabled else "disabled"
        embed = discord.Embed(
            description=f"{icon} Auto-warn for spam is now **{state}**.",
            color=discord.Color.green() if enabled else discord.Color.red(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ── Prefix Commands ───────────────────────────────────────────────────────

    @commands.command(name="autoroleset")
    @commands.has_permissions(manage_roles=True)
    async def autoroleset_prefix(self, ctx: commands.Context, role: discord.Role):
        if role >= ctx.guild.me.top_role:
            await ctx.reply(f"{E.get('error', '❌')} I cannot assign a role higher than my own.", mention_author=False)
            return
        storage.set_server_config(ctx.guild.id, autorole=str(role.id))
        embed = discord.Embed(
            description=f"{E.get('success', '✅')} Auto role set — new members will receive {role.mention} on join.",
            color=discord.Color.green(),
        )
        await ctx.reply(embed=embed, mention_author=False)

    @commands.command(name="autorolerm")
    @commands.has_permissions(manage_roles=True)
    async def autorolerm_prefix(self, ctx: commands.Context):
        storage.set_server_config(ctx.guild.id, autorole=None)
        embed = discord.Embed(
            description=f"{E.get('success', '✅')} Auto role removed — role assignment on join is disabled.",
            color=discord.Color.green(),
        )
        await ctx.reply(embed=embed, mention_author=False)

    @commands.command(name="autorolestatus")
    async def autorolestatus_prefix(self, ctx: commands.Context):
        cfg = storage.get_server_config(ctx.guild.id)
        role_id = cfg.get("autorole")
        if role_id:
            role = ctx.guild.get_role(int(role_id))
            desc = f"{E.get('success', '✅')} Auto role is set to {role.mention if role else '`Deleted role`'}."
        else:
            desc = f"{E.get('info', 'ℹ️')} No auto role configured. Use `>autoroleset @role` to configure one."
        embed = discord.Embed(description=desc, color=WHITE)
        await ctx.reply(embed=embed, mention_author=False)

    @commands.command(name="autokickset")
    @commands.has_permissions(kick_members=True)
    async def autokickset_prefix(self, ctx: commands.Context, days: int):
        if days <= 0:
            storage.set_server_config(ctx.guild.id, autokick_days=None)
            embed = discord.Embed(description=f"{E.get('success', '✅')} Auto-kick disabled.", color=discord.Color.green())
        else:
            storage.set_server_config(ctx.guild.id, autokick_days=days)
            embed = discord.Embed(
                description=f"{E.get('success', '✅')} Auto-kick set — members inactive for **{days} days** are eligible. Run `>inactive` to review.",
                color=discord.Color.orange(),
            )
        await ctx.reply(embed=embed, mention_author=False)

    @commands.command(name="autowarnspam")
    @commands.has_permissions(manage_guild=True)
    async def autowarnspam_prefix(self, ctx: commands.Context, toggle: str):
        enabled = _parse_bool(toggle)
        if enabled is None:
            await ctx.reply(f"{E.get('error', '❌')} Use `on` or `off`.", mention_author=False)
            return
        storage.set_server_config(ctx.guild.id, autowarn_spam=enabled)
        icon = E.get("success", "✅") if enabled else E.get("error", "❌")
        state = "enabled" if enabled else "disabled"
        embed = discord.Embed(
            description=f"{icon} Auto-warn for spam is now **{state}**.",
            color=discord.Color.green() if enabled else discord.Color.red(),
        )
        await ctx.reply(embed=embed, mention_author=False)

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(f"{E.get('error', '❌')} You lack the required permissions.", ephemeral=True)
        else:
            await interaction.response.send_message(f"{E.get('error', '❌')} Error: `{error}`", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(AutomationCog(bot))
