import discord
from discord.ext import commands
from discord import app_commands
from help_view import HelpMenuView
import emojis_loader as E
import config_loader
from checks import get_owner_id

WHITE = discord.Color.from_rgb(255, 255, 255)


async def _resolve_is_owner(bot: commands.Bot, user_id: int) -> bool:
    owner_id = get_owner_id()
    if not owner_id:
        try:
            app = await bot.application_info()
            owner_id = app.owner.id
        except Exception:
            return False
    return user_id == owner_id


async def _build_help_view(bot: commands.Bot, user_id: int) -> HelpMenuView:
    is_owner = await _resolve_is_owner(bot, user_id)

    owner_id = config_loader.get_owner_id()
    owner_name: str | None = None
    if owner_id:
        try:
            owner_user = bot.get_user(owner_id) or await bot.fetch_user(owner_id)
            owner_name = owner_user.display_name or owner_user.name
        except Exception:
            owner_name = str(owner_id)

    support_invite = config_loader.get_support_invite()

    return HelpMenuView(
        is_owner=is_owner,
        owner_name=owner_name,
        owner_id=owner_id,
        support_invite=support_invite,
    )


class UtilityCog(commands.Cog, name="Utility"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ── Slash Commands ────────────────────────────────────────────────────────

    @app_commands.command(name="ping", description="Check the bot's response latency.")
    async def ping_slash(self, interaction: discord.Interaction):
        latency_ms = round(self.bot.latency * 1000)
        embed = discord.Embed(
            description=f"{E.get('ping', '🏓')} WebSocket latency: `{latency_ms}ms`",
            color=WHITE,
        )
        embed.set_footer(text="Cybork")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="about", description="Learn about Cybork and what it does.")
    async def about_slash(self, interaction: discord.Interaction):
        embed = _about_embed()
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="help", description="Browse all Cybork commands in an interactive menu.")
    async def help_slash(self, interaction: discord.Interaction):
        view = await _build_help_view(self.bot, interaction.user.id)
        await interaction.response.send_message(view=view)

    # ── Prefix Commands ───────────────────────────────────────────────────────

    @commands.command(name="ping", aliases=["p"])
    async def ping_prefix(self, ctx: commands.Context):
        latency_ms = round(self.bot.latency * 1000)
        embed = discord.Embed(
            description=f"{E.get('ping', '🏓')} WebSocket latency: `{latency_ms}ms`",
            color=WHITE,
        )
        embed.set_footer(text="Cybork")
        await ctx.reply(embed=embed, mention_author=False)

    @commands.command(name="about", aliases=["info"])
    async def about_prefix(self, ctx: commands.Context):
        embed = _about_embed()
        await ctx.reply(embed=embed, mention_author=False)

    @commands.command(name="help", aliases=["h", "commands"])
    async def help_prefix(self, ctx: commands.Context):
        view = await _build_help_view(self.bot, ctx.author.id)
        await ctx.reply(view=view, mention_author=False)

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
            title=f"{E.get('bot', '🤖')} Cybork — Bot Info",
            color=WHITE,
        )
        embed.set_thumbnail(url=bot.user.display_avatar.url)
        embed.add_field(name="Latency",    value=f"`{latency}ms`",            inline=True)
        embed.add_field(name="Guilds",     value=f"`{guilds}`",               inline=True)
        embed.add_field(name="Members",    value=f"`{members:,}`",            inline=True)
        embed.add_field(name="Commands",   value=f"`{cmds}`",                 inline=True)
        embed.add_field(name="discord.py", value=f"`{discord.__version__}`",  inline=True)
        embed.add_field(name="Python",     value=f"`{sys.version.split()[0]}`", inline=True)
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
            missing = ", ".join(
                p.replace("_", " ").title() for p in error.missing_permissions
            )
            embed = discord.Embed(
                description=f"{E.get('lock', '🔒')} You need **{missing}** permission to use this command.",
                color=discord.Color.red(),
            )
            await ctx.reply(embed=embed, mention_author=False)
        elif isinstance(error, commands.BotMissingPermissions):
            missing = ", ".join(
                p.replace("_", " ").title() for p in error.missing_permissions
            )
            embed = discord.Embed(
                description=f"{E.get('error', '❌')} I need **{missing}** permission to do that.",
                color=discord.Color.red(),
            )
            await ctx.reply(embed=embed, mention_author=False)
        elif isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                description=f"{E.get('info', 'ℹ️')} Missing argument: `{error.param.name}`. Use `>help` for usage.",
                color=discord.Color.orange(),
            )
            await ctx.reply(embed=embed, mention_author=False)
        elif isinstance(error, commands.BadArgument):
            embed = discord.Embed(
                description=f"{E.get('error', '❌')} Invalid argument. Use `>help` for usage.",
                color=discord.Color.red(),
            )
            await ctx.reply(embed=embed, mention_author=False)
        else:
            embed = discord.Embed(
                description=f"{E.get('error', '❌')} Error: `{error}`",
                color=discord.Color.red(),
            )
            await ctx.reply(embed=embed, mention_author=False)


def _about_embed() -> discord.Embed:
    embed = discord.Embed(
        title=f"{E.get('scan', '🔍')} About Cybork",
        description=(
            "**Cybork** is a risk intelligence tool for Discord servers.\n\n"
            "It analyzes members using multiple signal layers:\n"
            f"` → ` **Static signals** — Account age, username structure\n"
            f"` → ` **Behavioral similarity** — Pattern matching with recent joins\n"
            f"` → ` **Cluster detection** — Join timing anomaly detection\n\n"
            "Results are *probabilistic* and should be used as indicators, not verdicts.\n\n"
            "**Prefix commands:** `>help`, `>ping`, `>about`, `>botinfo`"
        ),
        color=WHITE,
    )
    embed.set_footer(text="Cybork — Detect What Others Miss")
    return embed


async def setup(bot: commands.Bot):
    await bot.add_cog(UtilityCog(bot))
