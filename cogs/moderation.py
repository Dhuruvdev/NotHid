import re
import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timezone, timedelta
from typing import Optional

import storage
import emojis_loader as E

WHITE = discord.Color.from_rgb(255, 255, 255)


def parse_duration(text: str) -> Optional[timedelta]:
    m = re.fullmatch(r"(\d+)\s*([smhdw])", text.strip().lower())
    if not m:
        return None
    amount, unit = int(m.group(1)), m.group(2)
    return timedelta(seconds=amount * {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}[unit])


def _duration_label(td: timedelta) -> str:
    s = int(td.total_seconds())
    if s < 60:
        return f"{s}s"
    if s < 3600:
        return f"{s // 60}m"
    if s < 86400:
        return f"{s // 3600}h"
    return f"{s // 86400}d"


def _hierarchy_ok(interaction: discord.Interaction, target: discord.Member) -> bool:
    if target.id == interaction.guild.owner_id:
        return False
    if interaction.guild.me.top_role <= target.top_role:
        return False
    if interaction.user.top_role <= target.top_role:
        return False
    return True


def _hierarchy_ok_ctx(ctx: commands.Context, target: discord.Member) -> bool:
    if target.id == ctx.guild.owner_id:
        return False
    if ctx.guild.me.top_role <= target.top_role:
        return False
    if ctx.author.top_role <= target.top_role:
        return False
    return True


def _parse_bool(value: str) -> Optional[bool]:
    if value.lower() in ("on", "true", "yes", "enable", "1"):
        return True
    if value.lower() in ("off", "false", "no", "disable", "0"):
        return False
    return None


async def _send_mod_log(bot: commands.Bot, guild: discord.Guild, embed: discord.Embed) -> None:
    cfg = storage.get_server_config(guild.id)
    ch_id = cfg.get("mod_log_channel")
    if not ch_id:
        return
    ch = guild.get_channel(int(ch_id))
    if ch:
        try:
            await ch.send(embed=embed)
        except discord.Forbidden:
            pass


class ModerationCog(commands.Cog, name="Moderation"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ── Warn ────────────────────────────────────────────────────────────────

    @app_commands.command(name="warn", description="Issue a warning to a member.")
    @app_commands.describe(user="The member to warn", reason="Reason for the warning")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def warn(self, interaction: discord.Interaction, user: discord.Member, reason: str = "No reason provided"):
        if not _hierarchy_ok(interaction, user):
            await interaction.response.send_message(f"{E.get('error', '❌')} You cannot warn that member.", ephemeral=True)
            return

        entry = storage.add_warning(user.id, interaction.guild_id, reason, interaction.user.id)
        storage.add_mod_action(user.id, interaction.guild_id, "WARN", reason, interaction.user.id)
        total = len(storage.get_warnings(user.id, interaction.guild_id))

        embed = discord.Embed(
            title=f"{E.get('warn_icon', '⚠️')} Warning Issued",
            color=discord.Color.yellow(),
            timestamp=datetime.now(timezone.utc),
        )
        embed.add_field(name="Member", value=user.mention, inline=True)
        embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
        embed.add_field(name="Total Warnings", value=f"`{total}`", inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.set_footer(text=f"Warning ID: {entry['id']}  ·  Cybork Moderation")
        embed.set_thumbnail(url=user.display_avatar.url)
        await interaction.response.send_message(embed=embed)

        try:
            await user.send(embed=discord.Embed(
                description=f"{E.get('warn_icon', '⚠️')} You received a warning in **{interaction.guild.name}**\n**Reason:** {reason}",
                color=discord.Color.yellow(),
            ))
        except Exception:
            pass

        await _send_mod_log(self.bot, interaction.guild, embed)

    # ── Mute (Timeout) ──────────────────────────────────────────────────────

    @app_commands.command(name="mute", description="Timeout (mute) a member for a specified duration.")
    @app_commands.describe(user="The member to mute", duration="Duration (e.g. 10m, 2h, 1d)", reason="Reason")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def mute(self, interaction: discord.Interaction, user: discord.Member, duration: str, reason: str = "No reason provided"):
        if not _hierarchy_ok(interaction, user):
            await interaction.response.send_message(f"{E.get('error', '❌')} You cannot mute that member.", ephemeral=True)
            return

        td = parse_duration(duration)
        if not td or td.total_seconds() > 2419200:
            await interaction.response.send_message(
                f"{E.get('error', '❌')} Invalid duration. Use formats like `10m`, `2h`, `1d`. Max: 28 days.", ephemeral=True
            )
            return

        until = datetime.now(timezone.utc) + td
        await user.timeout(until, reason=reason)
        storage.add_mod_action(user.id, interaction.guild_id, "MUTE", reason, interaction.user.id)

        embed = discord.Embed(
            title=f"{E.get('mute', '🔇')} Member Muted",
            color=discord.Color.orange(),
            timestamp=datetime.now(timezone.utc),
        )
        embed.add_field(name="Member", value=user.mention, inline=True)
        embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
        embed.add_field(name="Duration", value=f"`{_duration_label(td)}`", inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_footer(text="Cybork Moderation")
        await interaction.response.send_message(embed=embed)
        await _send_mod_log(self.bot, interaction.guild, embed)

    # ── Kick ────────────────────────────────────────────────────────────────

    @app_commands.command(name="kick", description="Kick a member from the server.")
    @app_commands.describe(user="The member to kick", reason="Reason")
    @app_commands.checks.has_permissions(kick_members=True)
    async def kick(self, interaction: discord.Interaction, user: discord.Member, reason: str = "No reason provided"):
        if not _hierarchy_ok(interaction, user):
            await interaction.response.send_message(f"{E.get('error', '❌')} You cannot kick that member.", ephemeral=True)
            return

        storage.add_mod_action(user.id, interaction.guild_id, "KICK", reason, interaction.user.id)

        embed = discord.Embed(
            title=f"{E.get('kick', '👢')} Member Kicked",
            color=discord.Color.red(),
            timestamp=datetime.now(timezone.utc),
        )
        embed.add_field(name="Member", value=f"{user} (`{user.id}`)", inline=True)
        embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_footer(text="Cybork Moderation")

        await interaction.response.send_message(embed=embed)
        try:
            await user.send(embed=discord.Embed(
                description=f"{E.get('kick', '👢')} You were kicked from **{interaction.guild.name}**\n**Reason:** {reason}",
                color=discord.Color.red(),
            ))
        except Exception:
            pass
        await user.kick(reason=f"{reason} | by {interaction.user}")
        await _send_mod_log(self.bot, interaction.guild, embed)

    # ── Ban ─────────────────────────────────────────────────────────────────

    @app_commands.command(name="ban", description="Ban a member from the server.")
    @app_commands.describe(user="The member to ban", reason="Reason", delete_days="Days of messages to delete (0-7)")
    @app_commands.checks.has_permissions(ban_members=True)
    async def ban(self, interaction: discord.Interaction, user: discord.Member, reason: str = "No reason provided", delete_days: int = 0):
        if not _hierarchy_ok(interaction, user):
            await interaction.response.send_message(f"{E.get('error', '❌')} You cannot ban that member.", ephemeral=True)
            return

        delete_days = max(0, min(7, delete_days))
        storage.add_mod_action(user.id, interaction.guild_id, "BAN", reason, interaction.user.id)

        embed = discord.Embed(
            title=f"{E.get('ban', '🔨')} Member Banned",
            color=discord.Color.dark_red(),
            timestamp=datetime.now(timezone.utc),
        )
        embed.add_field(name="Member", value=f"{user} (`{user.id}`)", inline=True)
        embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
        embed.add_field(name="Delete History", value=f"`{delete_days}d`", inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_footer(text="Cybork Moderation")

        await interaction.response.send_message(embed=embed)
        try:
            await user.send(embed=discord.Embed(
                description=f"{E.get('ban', '🔨')} You were banned from **{interaction.guild.name}**\n**Reason:** {reason}",
                color=discord.Color.dark_red(),
            ))
        except Exception:
            pass
        await user.ban(reason=f"{reason} | by {interaction.user}", delete_message_days=delete_days)
        await _send_mod_log(self.bot, interaction.guild, embed)

    # ── Channel Controls ─────────────────────────────────────────────────────

    @app_commands.command(name="lock", description="Lock a channel so members cannot send messages.")
    @app_commands.describe(channel="Channel to lock (defaults to current)", reason="Reason")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def lock(self, interaction: discord.Interaction, channel: discord.TextChannel = None, reason: str = "No reason provided"):
        ch = channel or interaction.channel
        overwrite = ch.overwrites_for(interaction.guild.default_role)
        overwrite.send_messages = False
        await ch.set_permissions(interaction.guild.default_role, overwrite=overwrite, reason=reason)
        embed = discord.Embed(
            description=f"{E.get('lock', '🔒')} {ch.mention} has been **locked** — {reason}",
            color=discord.Color.red(),
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="unlock", description="Unlock a channel so members can send messages.")
    @app_commands.describe(channel="Channel to unlock (defaults to current)", reason="Reason")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def unlock(self, interaction: discord.Interaction, channel: discord.TextChannel = None, reason: str = "No reason provided"):
        ch = channel or interaction.channel
        overwrite = ch.overwrites_for(interaction.guild.default_role)
        overwrite.send_messages = None
        await ch.set_permissions(interaction.guild.default_role, overwrite=overwrite, reason=reason)
        embed = discord.Embed(
            description=f"{E.get('unlock', '🔓')} {ch.mention} has been **unlocked** — {reason}",
            color=discord.Color.green(),
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="slowmode", description="Set slowmode for a channel.")
    @app_commands.describe(seconds="Slowmode delay in seconds (0 to disable)", channel="Target channel")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def slowmode(self, interaction: discord.Interaction, seconds: int, channel: discord.TextChannel = None):
        ch = channel or interaction.channel
        seconds = max(0, min(21600, seconds))
        await ch.edit(slowmode_delay=seconds)
        desc = (
            f"{E.get('success', '✅')} Slowmode **disabled** in {ch.mention}."
            if seconds == 0 else
            f"{E.get('info', 'ℹ️')} Slowmode set to `{seconds}s` in {ch.mention}."
        )
        embed = discord.Embed(description=desc, color=WHITE)
        await interaction.response.send_message(embed=embed)

    # ── Server Filters ────────────────────────────────────────────────────────

    @app_commands.command(name="antispam", description="Toggle anti-spam filter on or off.")
    @app_commands.describe(enabled="Turn on or off")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def antispam(self, interaction: discord.Interaction, enabled: bool):
        storage.set_server_config(interaction.guild_id, antispam=enabled)
        icon = E.get("success", "✅") if enabled else E.get("error", "❌")
        embed = discord.Embed(
            description=f"{icon} Anti-spam protection is now **{'enabled' if enabled else 'disabled'}**.",
            color=discord.Color.green() if enabled else discord.Color.red(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="antilink", description="Toggle anti-link filter (blocks external links).")
    @app_commands.describe(enabled="Turn on or off")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def antilink(self, interaction: discord.Interaction, enabled: bool):
        storage.set_server_config(interaction.guild_id, antilink=enabled)
        icon = E.get("success", "✅") if enabled else E.get("error", "❌")
        embed = discord.Embed(
            description=f"{icon} Anti-link protection is now **{'enabled' if enabled else 'disabled'}**.",
            color=discord.Color.green() if enabled else discord.Color.red(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="capsfilter", description="Toggle caps filter (blocks excessive caps).")
    @app_commands.describe(enabled="Turn on or off")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def capsfilter(self, interaction: discord.Interaction, enabled: bool):
        storage.set_server_config(interaction.guild_id, capsfilter=enabled)
        icon = E.get("success", "✅") if enabled else E.get("error", "❌")
        embed = discord.Embed(
            description=f"{icon} Caps filter is now **{'enabled' if enabled else 'disabled'}**.",
            color=discord.Color.green() if enabled else discord.Color.red(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ── Prefix Commands ───────────────────────────────────────────────────────

    @commands.command(name="warn")
    @commands.has_permissions(moderate_members=True)
    async def warn_prefix(self, ctx: commands.Context, user: discord.Member, *, reason: str = "No reason provided"):
        if not _hierarchy_ok_ctx(ctx, user):
            await ctx.reply(f"{E.get('error', '❌')} You cannot warn that member.", mention_author=False)
            return
        entry = storage.add_warning(user.id, ctx.guild.id, reason, ctx.author.id)
        storage.add_mod_action(user.id, ctx.guild.id, "WARN", reason, ctx.author.id)
        total = len(storage.get_warnings(user.id, ctx.guild.id))
        embed = discord.Embed(title=f"{E.get('warn_icon', '⚠️')} Warning Issued", color=discord.Color.yellow(), timestamp=datetime.now(timezone.utc))
        embed.add_field(name="Member", value=user.mention, inline=True)
        embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
        embed.add_field(name="Total Warnings", value=f"`{total}`", inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.set_footer(text=f"Warning ID: {entry['id']}  ·  Cybork Moderation")
        embed.set_thumbnail(url=user.display_avatar.url)
        await ctx.reply(embed=embed, mention_author=False)
        try:
            await user.send(embed=discord.Embed(
                description=f"{E.get('warn_icon', '⚠️')} You received a warning in **{ctx.guild.name}**\n**Reason:** {reason}",
                color=discord.Color.yellow(),
            ))
        except Exception:
            pass
        await _send_mod_log(self.bot, ctx.guild, embed)

    @commands.command(name="mute")
    @commands.has_permissions(moderate_members=True)
    async def mute_prefix(self, ctx: commands.Context, user: discord.Member, duration: str, *, reason: str = "No reason provided"):
        if not _hierarchy_ok_ctx(ctx, user):
            await ctx.reply(f"{E.get('error', '❌')} You cannot mute that member.", mention_author=False)
            return
        td = parse_duration(duration)
        if not td or td.total_seconds() > 2419200:
            await ctx.reply(f"{E.get('error', '❌')} Invalid duration. Use formats like `10m`, `2h`, `1d`. Max: 28 days.", mention_author=False)
            return
        until = datetime.now(timezone.utc) + td
        await user.timeout(until, reason=reason)
        storage.add_mod_action(user.id, ctx.guild.id, "MUTE", reason, ctx.author.id)
        embed = discord.Embed(title=f"{E.get('mute', '🔇')} Member Muted", color=discord.Color.orange(), timestamp=datetime.now(timezone.utc))
        embed.add_field(name="Member", value=user.mention, inline=True)
        embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
        embed.add_field(name="Duration", value=f"`{_duration_label(td)}`", inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_footer(text="Cybork Moderation")
        await ctx.reply(embed=embed, mention_author=False)
        await _send_mod_log(self.bot, ctx.guild, embed)

    @commands.command(name="kick")
    @commands.has_permissions(kick_members=True)
    async def kick_prefix(self, ctx: commands.Context, user: discord.Member, *, reason: str = "No reason provided"):
        if not _hierarchy_ok_ctx(ctx, user):
            await ctx.reply(f"{E.get('error', '❌')} You cannot kick that member.", mention_author=False)
            return
        storage.add_mod_action(user.id, ctx.guild.id, "KICK", reason, ctx.author.id)
        embed = discord.Embed(title=f"{E.get('kick', '👢')} Member Kicked", color=discord.Color.red(), timestamp=datetime.now(timezone.utc))
        embed.add_field(name="Member", value=f"{user} (`{user.id}`)", inline=True)
        embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_footer(text="Cybork Moderation")
        await ctx.reply(embed=embed, mention_author=False)
        try:
            await user.send(embed=discord.Embed(
                description=f"{E.get('kick', '👢')} You were kicked from **{ctx.guild.name}**\n**Reason:** {reason}",
                color=discord.Color.red(),
            ))
        except Exception:
            pass
        await user.kick(reason=f"{reason} | by {ctx.author}")
        await _send_mod_log(self.bot, ctx.guild, embed)

    @commands.command(name="ban")
    @commands.has_permissions(ban_members=True)
    async def ban_prefix(self, ctx: commands.Context, user: discord.Member, *, reason: str = "No reason provided"):
        if not _hierarchy_ok_ctx(ctx, user):
            await ctx.reply(f"{E.get('error', '❌')} You cannot ban that member.", mention_author=False)
            return
        storage.add_mod_action(user.id, ctx.guild.id, "BAN", reason, ctx.author.id)
        embed = discord.Embed(title=f"{E.get('ban', '🔨')} Member Banned", color=discord.Color.dark_red(), timestamp=datetime.now(timezone.utc))
        embed.add_field(name="Member", value=f"{user} (`{user.id}`)", inline=True)
        embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_footer(text="Cybork Moderation")
        await ctx.reply(embed=embed, mention_author=False)
        try:
            await user.send(embed=discord.Embed(
                description=f"{E.get('ban', '🔨')} You were banned from **{ctx.guild.name}**\n**Reason:** {reason}",
                color=discord.Color.dark_red(),
            ))
        except Exception:
            pass
        await user.ban(reason=f"{reason} | by {ctx.author}", delete_message_days=0)
        await _send_mod_log(self.bot, ctx.guild, embed)

    @commands.command(name="lock")
    @commands.has_permissions(manage_channels=True)
    async def lock_prefix(self, ctx: commands.Context, channel: discord.TextChannel = None, *, reason: str = "No reason provided"):
        ch = channel or ctx.channel
        overwrite = ch.overwrites_for(ctx.guild.default_role)
        overwrite.send_messages = False
        await ch.set_permissions(ctx.guild.default_role, overwrite=overwrite, reason=reason)
        embed = discord.Embed(description=f"{E.get('lock', '🔒')} {ch.mention} has been **locked** — {reason}", color=discord.Color.red())
        await ctx.reply(embed=embed, mention_author=False)

    @commands.command(name="unlock")
    @commands.has_permissions(manage_channels=True)
    async def unlock_prefix(self, ctx: commands.Context, channel: discord.TextChannel = None, *, reason: str = "No reason provided"):
        ch = channel or ctx.channel
        overwrite = ch.overwrites_for(ctx.guild.default_role)
        overwrite.send_messages = None
        await ch.set_permissions(ctx.guild.default_role, overwrite=overwrite, reason=reason)
        embed = discord.Embed(description=f"{E.get('unlock', '🔓')} {ch.mention} has been **unlocked** — {reason}", color=discord.Color.green())
        await ctx.reply(embed=embed, mention_author=False)

    @commands.command(name="slowmode")
    @commands.has_permissions(manage_channels=True)
    async def slowmode_prefix(self, ctx: commands.Context, seconds: int, channel: discord.TextChannel = None):
        ch = channel or ctx.channel
        seconds = max(0, min(21600, seconds))
        await ch.edit(slowmode_delay=seconds)
        desc = (
            f"{E.get('success', '✅')} Slowmode **disabled** in {ch.mention}."
            if seconds == 0 else
            f"{E.get('info', 'ℹ️')} Slowmode set to `{seconds}s` in {ch.mention}."
        )
        embed = discord.Embed(description=desc, color=WHITE)
        await ctx.reply(embed=embed, mention_author=False)

    @commands.command(name="antispam")
    @commands.has_permissions(manage_guild=True)
    async def antispam_prefix(self, ctx: commands.Context, toggle: str):
        enabled = _parse_bool(toggle)
        if enabled is None:
            await ctx.reply(f"{E.get('error', '❌')} Use `on` or `off`.", mention_author=False)
            return
        storage.set_server_config(ctx.guild.id, antispam=enabled)
        icon = E.get("success", "✅") if enabled else E.get("error", "❌")
        embed = discord.Embed(
            description=f"{icon} Anti-spam protection is now **{'enabled' if enabled else 'disabled'}**.",
            color=discord.Color.green() if enabled else discord.Color.red(),
        )
        await ctx.reply(embed=embed, mention_author=False)

    @commands.command(name="antilink")
    @commands.has_permissions(manage_guild=True)
    async def antilink_prefix(self, ctx: commands.Context, toggle: str):
        enabled = _parse_bool(toggle)
        if enabled is None:
            await ctx.reply(f"{E.get('error', '❌')} Use `on` or `off`.", mention_author=False)
            return
        storage.set_server_config(ctx.guild.id, antilink=enabled)
        icon = E.get("success", "✅") if enabled else E.get("error", "❌")
        embed = discord.Embed(
            description=f"{icon} Anti-link protection is now **{'enabled' if enabled else 'disabled'}**.",
            color=discord.Color.green() if enabled else discord.Color.red(),
        )
        await ctx.reply(embed=embed, mention_author=False)

    @commands.command(name="capsfilter")
    @commands.has_permissions(manage_guild=True)
    async def capsfilter_prefix(self, ctx: commands.Context, toggle: str):
        enabled = _parse_bool(toggle)
        if enabled is None:
            await ctx.reply(f"{E.get('error', '❌')} Use `on` or `off`.", mention_author=False)
            return
        storage.set_server_config(ctx.guild.id, capsfilter=enabled)
        icon = E.get("success", "✅") if enabled else E.get("error", "❌")
        embed = discord.Embed(
            description=f"{icon} Caps filter is now **{'enabled' if enabled else 'disabled'}**.",
            color=discord.Color.green() if enabled else discord.Color.red(),
        )
        await ctx.reply(embed=embed, mention_author=False)

    # ── Error Handlers ────────────────────────────────────────────────────────

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(f"{E.get('error', '❌')} You don't have permission to use this command.", ephemeral=True)
        elif isinstance(error, app_commands.BotMissingPermissions):
            await interaction.response.send_message(f"{E.get('error', '❌')} I don't have the required permissions for this action.", ephemeral=True)
        else:
            await interaction.response.send_message(f"{E.get('error', '❌')} An error occurred: `{error}`", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(ModerationCog(bot))
