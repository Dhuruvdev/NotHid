import os
import sys
import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timezone

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



class OwnerCog(commands.Cog, name="Owner"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _is_owner(self, user_id: int) -> bool:
        owner_id = config_loader.get_owner_id()
        if owner_id:
            return user_id == owner_id
        app = await self.bot.application_info()
        return user_id == app.owner.id

    # ── np @user — grant / revoke noprefix access ────────────────────────────

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Owner-only: `np @user` toggles noprefix command access for the mentioned user."""
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
                description=(
                    f"{E.get('info', 'ℹ️')} **Usage:** `np @user`\n"
                    f"Grants or revokes noprefix command access for that user.\n"
                    f"Run again on the same user to remove their access."
                ),
                color=WHITE,
            )
            await message.reply(embed=embed, mention_author=False)
            return

        target = message.mentions[0]

        if target.bot:
            embed = discord.Embed(
                description=f"{E.get('error', '❌')} Bots cannot be granted noprefix access.",
                color=discord.Color.red(),
            )
            await message.reply(embed=embed, mention_author=False)
            return

        added = config_loader.toggle_noprefix_user(target.id)

        if added:
            embed = discord.Embed(
                description=(
                    f"{E.get('success', '✅')} **Noprefix granted** to {target.mention}\n"
                    f"They can now run commands without the `>` prefix."
                ),
                color=discord.Color.green(),
            )
        else:
            embed = discord.Embed(
                description=(
                    f"{E.get('lock', '🔒')} **Noprefix revoked** from {target.mention}\n"
                    f"They must use the `>` prefix again."
                ),
                color=discord.Color.orange(),
            )

        embed.set_footer(text=f"Requested by {message.author} • Cybork")
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

    # ── Set Support Invite ────────────────────────────────────────────────────

    @commands.command(name="setsupport")
    async def setsupport(self, ctx: commands.Context, *, invite_url: str = ""):
        """
        >setsupport <invite_url>  — Set the support server invite shown in >help.
        Use >setsupport clear to remove it. Only usable by the configured owner.
        """
        if not await self._is_owner(ctx.author.id):
            embed = discord.Embed(
                description=f"{E.get('lock', '🔒')} This command is restricted to the bot owner.",
                color=discord.Color.red(),
            )
            await ctx.reply(embed=embed, mention_author=False)
            return

        url = invite_url.strip()

        if url.lower() == "clear" or not url:
            config_loader.set_support_invite(None)
            embed = discord.Embed(
                description=f"{E.get('success', '✅')} Support server invite cleared.",
                color=discord.Color.green(),
            )
            await ctx.reply(embed=embed, mention_author=False)
            return

        if not (url.startswith("https://discord.gg/") or url.startswith("https://discord.com/")):
            embed = discord.Embed(
                description=(
                    f"{E.get('error', '❌')} Invalid invite URL. "
                    f"Must start with `https://discord.gg/` or `https://discord.com/`."
                ),
                color=discord.Color.red(),
            )
            await ctx.reply(embed=embed, mention_author=False)
            return

        config_loader.set_support_invite(url)
        embed = discord.Embed(
            description=f"{E.get('success', '✅')} Support server invite set to <{url}>.",
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
