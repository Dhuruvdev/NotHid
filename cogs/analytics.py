import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timezone

import storage


class AnalyticsCog(commands.Cog, name="Analytics"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ── Slash Commands ────────────────────────────────────────────────────────

    @app_commands.command(name="serverstats", description="View overall server statistics.")
    async def serverstats(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True, ephemeral=True)
        embed = _build_serverstats(interaction.guild)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="topusers", description="View the most active members in this server.")
    async def topusers(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True, ephemeral=True)
        embed = _build_topusers(interaction.guild, interaction.guild_id)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="inactive", description="List members with no tracked activity.")
    async def inactive(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True, ephemeral=True)
        embed = _build_inactive(interaction.guild, interaction.guild_id)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="channels", description="View channel activity overview (dead vs active).")
    async def channels(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True, ephemeral=True)
        embed = _build_channels(interaction.guild)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="report", description="Generate a full server health report.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def report(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        embed = _build_report(interaction.guild)
        await interaction.followup.send(embed=embed)

    # ── Prefix Commands ───────────────────────────────────────────────────────

    @commands.command(name="serverstats")
    async def serverstats_prefix(self, ctx: commands.Context):
        async with ctx.typing():
            embed = _build_serverstats(ctx.guild)
            await ctx.reply(embed=embed, mention_author=False)

    @commands.command(name="topusers")
    async def topusers_prefix(self, ctx: commands.Context):
        async with ctx.typing():
            embed = _build_topusers(ctx.guild, ctx.guild.id)
            await ctx.reply(embed=embed, mention_author=False)

    @commands.command(name="inactive")
    async def inactive_prefix(self, ctx: commands.Context):
        async with ctx.typing():
            embed = _build_inactive(ctx.guild, ctx.guild.id)
            await ctx.reply(embed=embed, mention_author=False)

    @commands.command(name="channels")
    async def channels_prefix(self, ctx: commands.Context):
        async with ctx.typing():
            embed = _build_channels(ctx.guild)
            await ctx.reply(embed=embed, mention_author=False)

    @commands.command(name="report")
    @commands.has_permissions(manage_guild=True)
    async def report_prefix(self, ctx: commands.Context):
        async with ctx.typing():
            embed = _build_report(ctx.guild)
            await ctx.reply(embed=embed, mention_author=False)

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("❌ You need `Manage Server` permission.", ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ Error: `{error}`", ephemeral=True)


def _build_serverstats(guild: discord.Guild) -> discord.Embed:
    now = datetime.now(timezone.utc)
    total = guild.member_count or 0
    humans = sum(1 for m in guild.members if not m.bot)
    bots = total - humans
    online = sum(1 for m in guild.members if m.status != discord.Status.offline)
    age_days = (now - guild.created_at).days
    text_ch = len(guild.text_channels)
    voice_ch = len(guild.voice_channels)
    roles = len(guild.roles) - 1
    boost_tier = guild.premium_tier
    boosters = guild.premium_subscription_count or 0

    new_7d = 0
    new_30d = 0
    for m in guild.members:
        if m.joined_at:
            diff = (now - m.joined_at).days
            if diff <= 7:
                new_7d += 1
            if diff <= 30:
                new_30d += 1

    embed = discord.Embed(title=f"Server Statistics — {guild.name}", color=discord.Color.blurple(), timestamp=now)
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    embed.add_field(name="👥 Total Members", value=f"`{total:,}`", inline=True)
    embed.add_field(name="🧑 Humans", value=f"`{humans:,}`", inline=True)
    embed.add_field(name="🤖 Bots", value=f"`{bots:,}`", inline=True)
    embed.add_field(name="🟢 Online", value=f"`{online:,}`", inline=True)
    embed.add_field(name="📥 Joined (7d)", value=f"`{new_7d}`", inline=True)
    embed.add_field(name="📥 Joined (30d)", value=f"`{new_30d}`", inline=True)
    embed.add_field(name="📁 Channels", value=f"`{text_ch}` text · `{voice_ch}` voice", inline=True)
    embed.add_field(name="🏷️ Roles", value=f"`{roles}`", inline=True)
    embed.add_field(name="⚡ Boost Tier", value=f"`Tier {boost_tier}` ({boosters} boosts)", inline=True)
    embed.add_field(
        name="🗓 Server Age",
        value=f"`{age_days // 365}y {(age_days % 365) // 30}mo`\n*Created {guild.created_at.strftime('%b %d, %Y')}*",
        inline=False,
    )
    embed.set_footer(text="Cybork Analytics")
    return embed


def _build_topusers(guild: discord.Guild, guild_id: int) -> discord.Embed:
    top = storage.get_top_users(guild_id, limit=10)
    embed = discord.Embed(title=f"Top Active Members — {guild.name}", color=discord.Color.blurple())
    if not top:
        embed.description = "No message activity tracked yet.\n*Cybork records messages from the point it joined.*"
    else:
        lines = []
        medals = ["🥇", "🥈", "🥉"]
        for i, (uid, data) in enumerate(top):
            member = guild.get_member(int(uid))
            name = member.display_name if member else f"User {uid}"
            medal = medals[i] if i < 3 else f"`{i+1}.`"
            lines.append(f"{medal} **{name}** — `{data['total']:,}` messages")
        embed.description = "\n".join(lines)
    embed.set_footer(text="Cybork Analytics · Data tracked since bot joined")
    return embed


def _build_inactive(guild: discord.Guild, guild_id: int) -> discord.Embed:
    cfg = storage.get_server_config(guild_id)
    threshold_days = cfg.get("autokick_days")
    now = datetime.now(timezone.utc)

    inactive_members = []
    for member in guild.members:
        if member.bot:
            continue
        act = storage.get_user_activity(member.id, guild_id)
        if act["total"] == 0:
            joined_days = (now - member.joined_at).days if member.joined_at else 0
            inactive_members.append((member, joined_days))

    inactive_members.sort(key=lambda x: x[1], reverse=True)

    embed = discord.Embed(
        title=f"Inactive Members — {guild.name}",
        description="Members with **zero tracked messages** since Cybork joined.",
        color=discord.Color.orange(),
    )
    if threshold_days:
        embed.description += f"\n*Auto-kick threshold: `{threshold_days}d` (set via >autokickset)*"

    if not inactive_members:
        embed.description += "\n\n✅ All members have some tracked activity."
    else:
        lines = []
        for member, joined_days in inactive_members[:15]:
            lines.append(f"` → ` {member.mention} — joined `{joined_days}d` ago")
        embed.add_field(
            name=f"Inactive Members ({len(inactive_members)} total, showing 15)",
            value="\n".join(lines) or "None",
            inline=False,
        )
    embed.set_footer(text="Cybork Analytics · Use >autokickset to configure auto-removal")
    return embed


def _build_channels(guild: discord.Guild) -> discord.Embed:
    all_activity: dict[str, int] = {}
    data_store = storage._load()
    prefix = f"{guild.id}:"
    for key, act in data_store.get("message_activity", {}).items():
        if not key.startswith(prefix):
            continue
        for ch_id, count in act.get("channels", {}).items():
            all_activity[ch_id] = all_activity.get(ch_id, 0) + count

    sorted_ch = sorted(all_activity.items(), key=lambda x: x[1], reverse=True)
    active = sorted_ch[:5]
    dead_ids = {c.id for c in guild.text_channels} - {int(cid) for cid, _ in all_activity.items()}

    embed = discord.Embed(title=f"Channel Activity — {guild.name}", color=discord.Color.blurple())

    if active:
        lines = []
        for cid, count in active:
            ch = guild.get_channel(int(cid))
            name = ch.mention if ch else f"<#{cid}>"
            lines.append(f"` → ` {name} — `{count:,}` messages")
        embed.add_field(name="🔥 Most Active", value="\n".join(lines), inline=False)
    else:
        embed.add_field(name="🔥 Most Active", value="No data tracked yet.", inline=False)

    if dead_ids:
        dead_mentions = [guild.get_channel(cid).mention for cid in list(dead_ids)[:8] if guild.get_channel(cid)]
        embed.add_field(
            name=f"💤 No Activity ({len(dead_ids)} channels)",
            value=" ".join(dead_mentions) or "None",
            inline=False,
        )

    embed.set_footer(text="Cybork Analytics · Tracked since bot joined")
    return embed


def _build_report(guild: discord.Guild) -> discord.Embed:
    now = datetime.now(timezone.utc)
    total = guild.member_count or 0
    humans = sum(1 for m in guild.members if not m.bot)
    new_7d = sum(1 for m in guild.members if m.joined_at and (now - m.joined_at).days <= 7)
    top = storage.get_top_users(guild.id, limit=3)
    all_flags = storage.get_all_flags(guild.id)
    cfg = storage.get_server_config(guild.id)

    embed = discord.Embed(
        title=f"🏥 Server Health Report — {guild.name}",
        color=discord.Color.from_rgb(124, 58, 237),
        timestamp=now,
    )
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)

    embed.add_field(name="👥 Members", value=f"`{humans:,}` humans · `{total - humans}` bots", inline=True)
    embed.add_field(name="📥 New (7d)", value=f"`{new_7d}`", inline=True)
    embed.add_field(name="🚩 Flagged", value=f"`{len(all_flags)}`", inline=True)

    protection_lines = [
        f"{'✅' if cfg['antispam'] else '❌'} Anti-Spam",
        f"{'✅' if cfg['antilink'] else '❌'} Anti-Link",
        f"{'✅' if cfg['capsfilter'] else '❌'} Caps Filter",
        f"{'✅' if cfg['risk_alerts'] else '❌'} Risk Alerts",
    ]
    embed.add_field(name="🛡️ Protection Status", value="\n".join(protection_lines), inline=True)

    if top:
        top_lines = []
        for uid, data in top:
            m = guild.get_member(int(uid))
            name = m.display_name if m else f"User {uid}"
            top_lines.append(f"` → ` **{name}** `{data['total']:,}` msgs")
        embed.add_field(name="📊 Top Members", value="\n".join(top_lines), inline=True)

    embed.set_footer(text="Cybork Server Health Report")
    return embed


async def setup(bot: commands.Bot):
    await bot.add_cog(AnalyticsCog(bot))
