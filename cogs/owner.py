import os
import sys
import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timezone

from checks import is_owner, get_owner_id

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

    async def _owner_guard(self, interaction: discord.Interaction) -> bool:
        owner_id = get_owner_id()
        if owner_id:
            return interaction.user.id == owner_id
        app = await self.bot.application_info()
        return interaction.user.id == app.owner.id

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
                f"✅ Synced `{len(synced)}` command(s) to **{interaction.guild.name}** (instant).", ephemeral=True
            )
        else:
            synced = await self.bot.tree.sync()
            await interaction.followup.send(
                f"✅ Synced `{len(synced)}` command(s) globally (propagation takes up to 1 hour).", ephemeral=True
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
                    results.append(f"✅ `{ext}`")
                except Exception as e:
                    results.append(f"❌ `{ext}` — {e}")
            await interaction.followup.send("\n".join(results), ephemeral=True)
        else:
            ext = f"cogs.{extension}" if not extension.startswith("cogs.") else extension
            try:
                await self.bot.reload_extension(ext)
                await interaction.followup.send(f"✅ Reloaded `{ext}`.", ephemeral=True)
            except Exception as e:
                await interaction.followup.send(f"❌ Failed to reload `{ext}`:\n```{e}```", ephemeral=True)

    # ── Status ───────────────────────────────────────────────────────────────

    @app_commands.command(name="status", description="[Owner] Change the bot's activity status.")
    @app_commands.describe(text="Status text", kind="Activity type")
    @app_commands.choices(kind=[
        app_commands.Choice(name="Watching", value="watching"),
        app_commands.Choice(name="Playing", value="playing"),
        app_commands.Choice(name="Listening", value="listening"),
        app_commands.Choice(name="Competing", value="competing"),
    ])
    @is_owner()
    async def status(self, interaction: discord.Interaction, text: str, kind: str = "watching"):
        types = {
            "watching": discord.ActivityType.watching,
            "playing": discord.ActivityType.playing,
            "listening": discord.ActivityType.listening,
            "competing": discord.ActivityType.competing,
        }
        await self.bot.change_presence(
            activity=discord.Activity(type=types[kind], name=text)
        )
        await interaction.response.send_message(
            f"✅ Status set to **{kind.capitalize()}** `{text}`.", ephemeral=True
        )

    # ── Bot Info ─────────────────────────────────────────────────────────────

    @app_commands.command(name="botinfo", description="[Owner] View detailed bot statistics.")
    @is_owner()
    async def botinfo(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)

        bot = self.bot
        uptime = datetime.now(timezone.utc) - bot.start_time if hasattr(bot, "start_time") else None
        guilds = len(bot.guilds)
        members = sum(g.member_count or 0 for g in bot.guilds)
        cogs_loaded = len(bot.cogs)
        cmds = len(list(bot.tree.walk_commands()))
        latency = round(bot.latency * 1000)

        owner_id = get_owner_id()
        owner_mention = f"<@{owner_id}>" if owner_id else "Not set"

        embed = discord.Embed(
            title="NotHide — Bot Info",
            color=discord.Color.from_rgb(124, 58, 237),
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_thumbnail(url=bot.user.display_avatar.url)
        embed.add_field(name="Owner", value=owner_mention, inline=True)
        embed.add_field(name="Latency", value=f"`{latency}ms`", inline=True)
        embed.add_field(name="Guilds", value=f"`{guilds}`", inline=True)
        embed.add_field(name="Members", value=f"`{members:,}`", inline=True)
        embed.add_field(name="Commands", value=f"`{cmds}`", inline=True)
        embed.add_field(name="Cogs Loaded", value=f"`{cogs_loaded}`", inline=True)
        if uptime:
            h, rem = divmod(int(uptime.total_seconds()), 3600)
            m, s = divmod(rem, 60)
            embed.add_field(name="Uptime", value=f"`{h}h {m}m {s}s`", inline=True)
        embed.add_field(name="discord.py", value=f"`{discord.__version__}`", inline=True)
        embed.add_field(name="Python", value=f"`{sys.version.split()[0]}`", inline=True)
        embed.set_footer(text="NotHide Owner Panel")
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
        embed.set_footer(text="NotHide Announcement")
        await channel.send(embed=embed)
        await interaction.response.send_message(f"✅ Announcement sent to {channel.mention}.", ephemeral=True)

    # ── Shutdown ─────────────────────────────────────────────────────────────

    @app_commands.command(name="shutdown", description="[Owner] Gracefully shut down the bot.")
    @is_owner()
    async def shutdown(self, interaction: discord.Interaction):
        await interaction.response.send_message("⚠️ Shutting down NotHide...", ephemeral=True)
        await self.bot.close()

    # ── Error handler ─────────────────────────────────────────────────────────

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CheckFailure):
            await interaction.response.send_message(
                "🔒 This command is restricted to the bot owner.", ephemeral=True
            )
        else:
            await interaction.response.send_message(f"❌ Error: `{error}`", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(OwnerCog(bot))
