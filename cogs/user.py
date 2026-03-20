import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timezone

import storage
from image_generator import generate_profile_card, generate_activity_card


def _humanize_delta(days: int) -> str:
    if days < 1:
        return "Today"
    if days < 30:
        return f"{days}d"
    if days < 365:
        return f"{days // 30}mo {days % 30}d"
    y, rem = divmod(days, 365)
    return f"{y}y {rem // 30}mo"


def _humanize_ago(dt_str: str) -> str:
    try:
        dt = datetime.fromisoformat(dt_str)
        diff = (datetime.now(timezone.utc) - dt).total_seconds()
        if diff < 60:
            return "Just now"
        if diff < 3600:
            return f"{int(diff // 60)}m ago"
        if diff < 86400:
            return f"{int(diff // 3600)}h ago"
        return f"{int(diff // 86400)}d ago"
    except Exception:
        return "Unknown"


async def _make_profile(user: discord.Member, guild_id: int):
    avatar_bytes = None
    try:
        avatar_bytes = await user.display_avatar.replace(format="png", size=256).read()
    except Exception:
        pass

    activity = storage.get_user_activity(user.id, guild_id)
    warnings = storage.get_warnings(user.id, guild_id)
    flag = storage.get_flag(user.id, guild_id)

    now = datetime.now(timezone.utc)
    account_age_days = (now - user.created_at).days
    joined_server_days = (now - user.joined_at).days if user.joined_at else None

    roles = []
    for r in reversed(user.roles):
        if r.is_default():
            continue
        color_val = r.color.value
        if color_val == 0:
            rgb = (80, 80, 100)
        else:
            rgb = ((color_val >> 16) & 0xFF, (color_val >> 8) & 0xFF, color_val & 0xFF)
        roles.append({"name": r.name, "color": rgb})

    top_role_color = (124, 58, 237)
    if user.top_role and user.top_role.color.value != 0:
        v = user.top_role.color.value
        top_role_color = ((v >> 16) & 0xFF, (v >> 8) & 0xFF, v & 0xFF)

    joined_server_str = _humanize_delta(joined_server_days) if joined_server_days is not None else "Unknown"
    created_str = user.created_at.strftime("%b %d, %Y")
    joined_str = user.joined_at.strftime("%b %d, %Y") if user.joined_at else "Unknown"

    card = generate_profile_card(
        username=user.name,
        display_name=user.display_name,
        user_id=str(user.id),
        account_age_days=account_age_days,
        created_str=created_str,
        joined_str=joined_str,
        joined_server_delta=joined_server_str,
        roles=roles[:10],
        avatar_bytes=avatar_bytes,
        is_bot=user.bot,
        is_booster=user.premium_since is not None,
        is_flagged=flag is not None,
        message_count=activity["total"],
        warning_count=len(warnings),
        top_role_color=top_role_color,
    )
    return card, top_role_color


async def _make_activity(user: discord.Member, guild_id: int, guild: discord.Guild):
    avatar_bytes = None
    try:
        avatar_bytes = await user.display_avatar.replace(format="png", size=256).read()
    except Exception:
        pass

    act = storage.get_user_activity(user.id, guild_id)
    total = act["total"]
    last_seen = act["last_seen"]

    top_channels = []
    if act["channels"]:
        sorted_ch = sorted(act["channels"].items(), key=lambda x: x[1], reverse=True)
        for ch_id, count in sorted_ch[:4]:
            ch = guild.get_channel(int(ch_id))
            name = f"#{ch.name}" if ch else f"#{ch_id}"
            top_channels.append({"name": name, "count": count})

    card = generate_activity_card(
        username=user.name,
        display_name=user.display_name,
        user_id=str(user.id),
        avatar_bytes=avatar_bytes,
        total_messages=total,
        last_seen_str=_humanize_ago(last_seen) if last_seen else "Not tracked",
        top_channels=top_channels,
    )
    return card


class UserCog(commands.Cog, name="User"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ── Slash Commands ────────────────────────────────────────────────────────

    @app_commands.command(name="profile", description="View a beautiful profile card for a server member.")
    @app_commands.describe(user="The member to view")
    async def profile(self, interaction: discord.Interaction, user: discord.Member):
        await interaction.response.defer(thinking=True)
        card, top_role_color = await _make_profile(user, interaction.guild_id)
        file = discord.File(card, filename="profile.png")
        embed = discord.Embed(title=f"Profile — {user.display_name}", color=discord.Color.from_rgb(*top_role_color))
        embed.set_image(url="attachment://profile.png")
        embed.set_footer(text="Cybork — Detect What Others Miss")
        await interaction.followup.send(embed=embed, file=file)

    @app_commands.command(name="activity", description="View a member's message activity report.")
    @app_commands.describe(user="The member to check")
    async def activity(self, interaction: discord.Interaction, user: discord.Member):
        await interaction.response.defer(thinking=True)
        card = await _make_activity(user, interaction.guild_id, interaction.guild)
        file = discord.File(card, filename="activity.png")
        embed = discord.Embed(title=f"Activity Report — {user.display_name}", color=discord.Color.blurple())
        embed.set_image(url="attachment://activity.png")
        embed.set_footer(text="Cybork tracks messages since the bot joined  ·  Data resets on rejoin")
        await interaction.followup.send(embed=embed, file=file)

    # ── Prefix Commands ───────────────────────────────────────────────────────

    @commands.command(name="profile")
    async def profile_prefix(self, ctx: commands.Context, user: discord.Member):
        async with ctx.typing():
            card, top_role_color = await _make_profile(user, ctx.guild.id)
            file = discord.File(card, filename="profile.png")
            embed = discord.Embed(title=f"Profile — {user.display_name}", color=discord.Color.from_rgb(*top_role_color))
            embed.set_image(url="attachment://profile.png")
            embed.set_footer(text="Cybork — Detect What Others Miss")
            await ctx.reply(embed=embed, file=file, mention_author=False)

    @commands.command(name="activity")
    async def activity_prefix(self, ctx: commands.Context, user: discord.Member):
        async with ctx.typing():
            card = await _make_activity(user, ctx.guild.id, ctx.guild)
            file = discord.File(card, filename="activity.png")
            embed = discord.Embed(title=f"Activity Report — {user.display_name}", color=discord.Color.blurple())
            embed.set_image(url="attachment://activity.png")
            embed.set_footer(text="Cybork tracks messages since the bot joined  ·  Data resets on rejoin")
            await ctx.reply(embed=embed, file=file, mention_author=False)


async def setup(bot: commands.Bot):
    await bot.add_cog(UserCog(bot))
