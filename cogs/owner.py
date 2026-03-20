import os
import sys
import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timezone

import storage
import scoring
import emojis_loader as E
import config_loader
from checks import is_owner, get_owner_id

WHITE = discord.Color.from_rgb(255, 255, 255)

EXTENSIONS = [
    "cogs.utility",
    "cogs.user",
    "cogs.risk",
    "cogs.moderation",
    "cogs.history",
    "cogs.config",
    "cogs.automation",
    "cogs.analytics",
    "cogs.alerts",
    "cogs.owner",
]


def _fmt_dt(dt: datetime) -> str:
    return dt.strftime("%b %d, %Y") if dt else "Unknown"


def _age(dt: datetime) -> str:
    if not dt:
        return "?"
    days = (datetime.now(timezone.utc) - dt).days
    if days < 30:
        return f"{days}d"
    if days < 365:
        return f"{days // 30}mo {days % 30}d"
    y, rem = divmod(days, 365)
    return f"{y}y {rem // 30}mo"


def _risk_color(cls: str) -> discord.Color:
    return {"LOW": discord.Color.green(), "MEDIUM": discord.Color.yellow(), "HIGH": discord.Color.red()}.get(
        cls, discord.Color.greyple()
    )


def _risk_emoji(cls: str) -> str:
    return {
        "LOW":    E.get("risk_low",     "🟢"),
        "MEDIUM": E.get("risk_medium",  "🟡"),
        "HIGH":   E.get("risk_high",    "🔴"),
    }.get(cls, E.get("risk_unknown", "⚪"))


class OwnerCog(commands.Cog, name="Owner"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _is_owner(self, user_id: int) -> bool:
        owner_id = config_loader.get_owner_id()
        if owner_id:
            return user_id == owner_id
        app = await self.bot.application_info()
        return user_id == app.owner.id

    # ── np @user (no-prefix owner lookup) ────────────────────────────────────

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        content = message.content.strip()
        lower = content.lower()

        if not (lower.startswith("np ") or lower == "np"):
            return

        if not await self._is_owner(message.author.id):
            return

        if not message.mentions:
            embed = discord.Embed(
                description=f"{E.get('info', 'ℹ️')} `np @user` — owner member lookup panel.",
                color=WHITE,
            )
            await message.reply(embed=embed, mention_author=False)
            return

        target = message.mentions[0]
        member = message.guild.get_member(target.id)
        guild_id = message.guild.id
        now = datetime.now(timezone.utc)

        async with message.channel.typing():
            warnings    = storage.get_warnings(target.id, guild_id)
            mod_history = storage.get_mod_history(target.id, guild_id)
            flag        = storage.get_flag(target.id, guild_id)
            notes       = storage.get_notes(target.id, guild_id)
            activity    = storage.get_user_activity(target.id, guild_id)
            scan        = storage.get_scan_result(target.id, guild_id)
            guild_hist  = storage.get_guild_history(guild_id)
            risk        = scoring.calculate_risk(target, guild_hist)

        cls   = risk["classification"]
        score = risk["score"]

        embed = discord.Embed(
            title=f"{E.get('owner', '🔐')} Owner Access Panel — {target}",
            color=_risk_color(cls),
            timestamp=now,
        )
        embed.set_thumbnail(url=target.display_avatar.url)

        embed.add_field(
            name=f"{E.get('identity', '📌')} Identity",
            value=(
                f"**ID:** `{target.id}`\n"
                f"**Created:** {_fmt_dt(target.created_at)} (`{_age(target.created_at)}`)\n"
                f"**Bot:** {'Yes' if target.bot else 'No'}"
            ),
            inline=True,
        )

        if member:
            timeout_until = member.timed_out_until
            is_timed_out  = timeout_until and timeout_until > now
            roles         = [r for r in member.roles if not r.is_default()]
            timed_out_val = f"{E.get('warning', '⚠️')} Yes" if is_timed_out else "No"
            embed.add_field(
                name=f"{E.get('server', '🏠')} Server",
                value=(
                    f"**Joined:** {_fmt_dt(member.joined_at)} (`{_age(member.joined_at)}`)\n"
                    f"**Top Role:** {member.top_role.mention if member.top_role and not member.top_role.is_default() else '`None`'}\n"
                    f"**Roles:** `{len(roles)}`\n"
                    f"**Timed Out:** {timed_out_val}"
                ),
                inline=True,
            )
        else:
            embed.add_field(name=f"{E.get('server', '🏠')} Server", value="*Not in this server*", inline=True)

        embed.add_field(
            name=f"{_risk_emoji(cls)} Risk Assessment",
            value=(
                f"**Score:** `{score}/100` — **{cls}**\n"
                f"Static `{risk['breakdown']['static']}` · "
                f"Behavioral `{risk['breakdown']['behavioral']}` · "
                f"Cluster `{risk['breakdown']['cluster']}`"
            ),
            inline=False,
        )

        if risk["reasons"]:
            embed.add_field(
                name=f"{E.get('warning', '⚠️')} Risk Indicators",
                value="\n".join(f"` → ` {r}" for r in risk["reasons"][:5]),
                inline=False,
            )

        embed.add_field(
            name=f"{E.get('activity', '📊')} Activity",
            value=(
                f"**Messages:** `{activity['total']:,}`\n"
                f"**Last Seen:** {activity['last_seen'] or 'Not tracked'}"
            ),
            inline=True,
        )

        flag_val = f"{E.get('flag', '🚩')} {flag['reason']}" if flag else f"{E.get('success', '✅')} Clear"
        embed.add_field(
            name=f"{E.get('moderation', '🛡️')} Moderation",
            value=(
                f"**Warnings:** `{len(warnings)}`\n"
                f"**Flag:** {flag_val}\n"
                f"**Actions:** `{len(mod_history)}`\n"
                f"**Notes:** `{len(notes)}`"
            ),
            inline=True,
        )

        if warnings:
            lw = warnings[-1]
            embed.add_field(
                name=f"{E.get('note', '📋')} Last Warning",
                value=f"`{lw['reason']}` — by <@{lw['moderator_id']}>",
                inline=False,
            )

        if scan:
            try:
                scan_dt  = datetime.fromisoformat(scan["timestamp"])
                scan_ago = f"<t:{int(scan_dt.timestamp())}:R>"
            except Exception:
                scan_ago = scan.get("timestamp", "?")
            embed.add_field(
                name=f"{E.get('scan', '🔍')} Last Scan",
                value=f"{scan_ago} — `{scan['result']['score']}/100` ({scan['result']['classification']})",
                inline=False,
            )

        embed.set_footer(text="Cybork — Owner Access Panel  ·  Only visible to you")

        await message.reply(embed=embed, mention_author=False)

        try:
            await message.delete()
        except (discord.Forbidden, discord.NotFound):
            pass

    # ── Sync ────────────────────────────────────────────────────────────────

    @app_commands.command(name="sync", description="[Owner] Sync slash commands to this guild or globally.")
    @app_commands.describe(scope="'guild' for instant sync, 'global' for all servers (up to 1hr)")
    @is_owner()
    async def sync(self, interaction: discord.Interaction, scope: str = "guild"):
        await interaction.response.defer(ephemeral=True, thinking=True)
        if scope == "guild":
            self.bot.tree.copy_global_to(guild=interaction.guild)
            synced = await self.bot.tree.sync(guild=interaction.guild)
            await interaction.followup.send(
                f"{E.get('success', '✅')} Synced `{len(synced)}` command(s) to **{interaction.guild.name}** (instant).",
                ephemeral=True,
            )
        else:
            synced = await self.bot.tree.sync()
            await interaction.followup.send(
                f"{E.get('success', '✅')} Synced `{len(synced)}` command(s) globally (up to 1 hour).",
                ephemeral=True,
            )

    # ── Reload ───────────────────────────────────────────────────────────────

    @app_commands.command(name="reload", description="[Owner] Reload a cog extension.")
    @app_commands.describe(extension="Cog name, e.g. 'risk', 'moderation', 'all'")
    @is_owner()
    async def reload(self, interaction: discord.Interaction, extension: str):
        await interaction.response.defer(ephemeral=True, thinking=True)
        if extension == "all":
            results = []
            for ext in EXTENSIONS:
                try:
                    await self.bot.reload_extension(ext)
                    results.append(f"{E.get('success', '✅')} `{ext}`")
                except Exception as e:
                    results.append(f"{E.get('error', '❌')} `{ext}` — {e}")
            await interaction.followup.send("\n".join(results), ephemeral=True)
        else:
            ext = f"cogs.{extension}" if not extension.startswith("cogs.") else extension
            try:
                await self.bot.reload_extension(ext)
                await interaction.followup.send(f"{E.get('success', '✅')} Reloaded `{ext}`.", ephemeral=True)
            except Exception as e:
                await interaction.followup.send(f"{E.get('error', '❌')} Failed: `{ext}`\n```{e}```", ephemeral=True)

    # ── Status ───────────────────────────────────────────────────────────────

    @app_commands.command(name="status", description="[Owner] Change the bot's activity status.")
    @app_commands.describe(text="Status text", kind="Activity type")
    @app_commands.choices(kind=[
        app_commands.Choice(name="Watching",   value="watching"),
        app_commands.Choice(name="Playing",    value="playing"),
        app_commands.Choice(name="Listening",  value="listening"),
        app_commands.Choice(name="Competing",  value="competing"),
    ])
    @is_owner()
    async def status(self, interaction: discord.Interaction, text: str, kind: str = "watching"):
        types = {
            "watching":  discord.ActivityType.watching,
            "playing":   discord.ActivityType.playing,
            "listening": discord.ActivityType.listening,
            "competing": discord.ActivityType.competing,
        }
        await self.bot.change_presence(activity=discord.Activity(type=types[kind], name=text))
        await interaction.response.send_message(
            f"{E.get('success', '✅')} Status → **{kind.capitalize()}** `{text}`.", ephemeral=True
        )

    # ── Bot Info ─────────────────────────────────────────────────────────────

    @app_commands.command(name="botinfo", description="[Owner] View detailed bot statistics.")
    @is_owner()
    async def botinfo(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        bot      = self.bot
        uptime   = datetime.now(timezone.utc) - bot.start_time if hasattr(bot, "start_time") else None
        guilds   = len(bot.guilds)
        members  = sum(g.member_count or 0 for g in bot.guilds)
        cogs_n   = len(bot.cogs)
        cmds     = len(list(bot.tree.walk_commands()))
        latency  = round(bot.latency * 1000)
        owner_id = config_loader.get_owner_id()

        embed = discord.Embed(
            title=f"{E.get('owner', '🔐')} Cybork — Bot Info",
            color=WHITE,
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_thumbnail(url=bot.user.display_avatar.url)
        embed.add_field(name="Owner",       value=f"<@{owner_id}>" if owner_id else "Not set", inline=True)
        embed.add_field(name="Latency",     value=f"`{latency}ms`",          inline=True)
        embed.add_field(name="Guilds",      value=f"`{guilds}`",              inline=True)
        embed.add_field(name="Members",     value=f"`{members:,}`",           inline=True)
        embed.add_field(name="Commands",    value=f"`{cmds}`",                inline=True)
        embed.add_field(name="Cogs",        value=f"`{cogs_n}`",              inline=True)
        if uptime:
            h, rem = divmod(int(uptime.total_seconds()), 3600)
            m, s   = divmod(rem, 60)
            embed.add_field(name="Uptime",  value=f"`{h}h {m}m {s}s`",      inline=True)
        embed.add_field(name="discord.py",  value=f"`{discord.__version__}`", inline=True)
        embed.add_field(name="Python",      value=f"`{sys.version.split()[0]}`", inline=True)
        embed.set_footer(text="Cybork Owner Panel")
        await interaction.followup.send(embed=embed, ephemeral=True)

    # ── Announce ─────────────────────────────────────────────────────────────

    @app_commands.command(name="announce", description="[Owner] Send an announcement to a channel.")
    @app_commands.describe(channel="Target channel", message="Announcement text")
    @is_owner()
    async def announce(self, interaction: discord.Interaction, channel: discord.TextChannel, message: str):
        embed = discord.Embed(
            description=message,
            color=discord.Color.from_rgb(124, 58, 237),
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_footer(text="Cybork Announcement")
        await channel.send(embed=embed)
        await interaction.response.send_message(
            f"{E.get('success', '✅')} Announcement sent to {channel.mention}.", ephemeral=True
        )

    # ── Shutdown ─────────────────────────────────────────────────────────────

    @app_commands.command(name="shutdown", description="[Owner] Gracefully shut down the bot.")
    @is_owner()
    async def shutdown(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            f"{E.get('warning', '⚠️')} Shutting down Cybork...", ephemeral=True
        )
        await self.bot.close()

    # ── Set Owner (prefix, bootstrap) ────────────────────────────────────────

    @commands.command(name="setowner")
    async def setowner(self, ctx: commands.Context, user_id: str = ""):
        """
        Bootstrap command: >setowner <discord_user_id>
        Can only be run when no owner is currently set in config.json,
        or by the already-configured owner.
        """
        current_owner = config_loader.get_owner_id()
        if current_owner and ctx.author.id != current_owner:
            embed = discord.Embed(
                description=f"{E.get('lock', '🔒')} Owner is already configured.",
                color=discord.Color.red(),
            )
            await ctx.reply(embed=embed, mention_author=False)
            return

        target_id = user_id.strip() or str(ctx.author.id)
        if not target_id.isdigit():
            embed = discord.Embed(
                description=f"{E.get('error', '❌')} Invalid user ID. Usage: `>setowner <discord_user_id>`",
                color=discord.Color.red(),
            )
            await ctx.reply(embed=embed, mention_author=False)
            return

        config_loader.set_owner_id(int(target_id))
        embed = discord.Embed(
            description=f"{E.get('success', '✅')} Owner set to <@{target_id}> (`{target_id}`) — saved to `data/config.json`.",
            color=discord.Color.green(),
        )
        await ctx.reply(embed=embed, mention_author=False)

    # ── Set Guild ─────────────────────────────────────────────────────────────

    @commands.command(name="setguild")
    async def setguild(self, ctx: commands.Context, guild_id: str = ""):
        """
        >setguild [guild_id]  — Set the guild ID for instant slash command sync.
        Only usable by the configured owner. Leave blank to use current guild.
        """
        if not await self._is_owner(ctx.author.id):
            embed = discord.Embed(
                description=f"{E.get('lock', '🔒')} This command is restricted to the bot owner.",
                color=discord.Color.red(),
            )
            await ctx.reply(embed=embed, mention_author=False)
            return

        gid = guild_id.strip() or str(ctx.guild.id)
        if not gid.isdigit():
            embed = discord.Embed(
                description=f"{E.get('error', '❌')} Invalid guild ID.",
                color=discord.Color.red(),
            )
            await ctx.reply(embed=embed, mention_author=False)
            return

        config_loader.set_guild_id(int(gid))
        embed = discord.Embed(
            description=f"{E.get('success', '✅')} Guild ID set to `{gid}` — saved to `data/config.json`.",
            color=discord.Color.green(),
        )
        await ctx.reply(embed=embed, mention_author=False)

    # ── Error Handler ─────────────────────────────────────────────────────────

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CheckFailure):
            await interaction.response.send_message(
                f"{E.get('lock', '🔒')} This command is restricted to the bot owner.", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"{E.get('error', '❌')} Error: `{error}`", ephemeral=True
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(OwnerCog(bot))
