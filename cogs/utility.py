import discord
from discord.ext import commands
from discord import app_commands
from help_view import HelpMenuView


class UtilityCog(commands.Cog, name="Utility"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ── Slash Commands ────────────────────────────────────────────────────────

    @app_commands.command(name="ping", description="Check the bot's response latency.")
    async def ping_slash(self, interaction: discord.Interaction):
        latency_ms = round(self.bot.latency * 1000)
        embed = discord.Embed(
            description=f"🏓 WebSocket latency: `{latency_ms}ms`",
            color=discord.Color.blurple(),
        )
        embed.set_footer(text="Cybork")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="about", description="Learn about Cybork and what it does.")
    async def about_slash(self, interaction: discord.Interaction):
        embed = _about_embed()
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="help", description="Browse all Cybork commands in an interactive menu.")
    async def help_slash(self, interaction: discord.Interaction):
        await interaction.response.send_message(view=HelpMenuView())

    # ── Prefix Commands ───────────────────────────────────────────────────────

    @commands.command(name="ping", aliases=["p"])
    async def ping_prefix(self, ctx: commands.Context):
        latency_ms = round(self.bot.latency * 1000)
        embed = discord.Embed(
            description=f"🏓 WebSocket latency: `{latency_ms}ms`",
            color=discord.Color.blurple(),
        )
        embed.set_footer(text="Cybork")
        await ctx.reply(embed=embed, mention_author=False)

    @commands.command(name="about", aliases=["info"])
    async def about_prefix(self, ctx: commands.Context):
        embed = _about_embed()
        await ctx.reply(embed=embed, mention_author=False)

    @commands.command(name="help", aliases=["h", "commands"])
    async def help_prefix(self, ctx: commands.Context):
        await ctx.reply(view=HelpMenuView(), mention_author=False)

    @commands.command(name="botinfo")
    async def botinfo_prefix(self, ctx: commands.Context):
        import sys
        from datetime import datetime, timezone
        bot = self.bot
        uptime = datetime.now(timezone.utc) - bot.start_time if hasattr(bot, "start_time") else None
        latency = round(bot.latency * 1000)
        guilds = len(bot.guilds)
        members = sum(g.member_count or 0 for g in bot.guilds)
        cmds = len(list(bot.tree.walk_commands()))
        embed = discord.Embed(
            title="Cybork — Bot Info",
            color=discord.Color.from_rgb(124, 58, 237),
        )
        embed.set_thumbnail(url=bot.user.display_avatar.url)
        embed.add_field(name="Latency", value=f"`{latency}ms`", inline=True)
        embed.add_field(name="Guilds", value=f"`{guilds}`", inline=True)
        embed.add_field(name="Members", value=f"`{members:,}`", inline=True)
        embed.add_field(name="Commands", value=f"`{cmds}`", inline=True)
        embed.add_field(name="discord.py", value=f"`{discord.__version__}`", inline=True)
        embed.add_field(name="Python", value=f"`{sys.version.split()[0]}`", inline=True)
        if uptime:
            h, rem = divmod(int(uptime.total_seconds()), 3600)
            m, s = divmod(rem, 60)
            embed.add_field(name="Uptime", value=f"`{h}h {m}m {s}s`", inline=True)
        embed.set_footer(text="Cybork")
        await ctx.reply(embed=embed, mention_author=False)

    # ── Prefix Error Handler ──────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.CommandNotFound):
            return
        if isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(
                description="❌ You don't have permission to use this command.",
                color=discord.Color.red(),
            )
            await ctx.reply(embed=embed, mention_author=False)
        elif isinstance(error, commands.BotMissingPermissions):
            embed = discord.Embed(
                description="❌ I don't have the required permissions for this action.",
                color=discord.Color.red(),
            )
            await ctx.reply(embed=embed, mention_author=False)
        else:
            embed = discord.Embed(
                description=f"❌ Error: `{error}`",
                color=discord.Color.red(),
            )
            await ctx.reply(embed=embed, mention_author=False)


def _about_embed() -> discord.Embed:
    embed = discord.Embed(
        title="About Cybork",
        description=(
            "**Cybork** is a risk intelligence tool for Discord servers.\n\n"
            "It analyzes members using multiple signal layers:\n"
            "` → ` **Static signals** — Account age, username structure\n"
            "` → ` **Behavioral similarity** — Pattern matching with recent joins\n"
            "` → ` **Cluster detection** — Join timing anomaly detection\n\n"
            "Results are *probabilistic* and should be used as indicators, not verdicts.\n\n"
            "**Slash commands:** `/help` to browse all commands\n"
            "**Prefix commands:** `>help`, `>ping`, `>about`, `>botinfo`"
        ),
        color=discord.Color.og_blurple(),
    )
    embed.set_footer(text="Cybork — Detect What Others Miss")
    return embed


async def setup(bot: commands.Bot):
    await bot.add_cog(UtilityCog(bot))
