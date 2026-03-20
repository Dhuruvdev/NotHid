import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timezone

import storage
import scoring
from image_generator import generate_card
from views import AnalysisView


def _risk_color(cls: str) -> discord.Color:
    return {"LOW": discord.Color.green(), "MEDIUM": discord.Color.yellow(), "HIGH": discord.Color.red()}.get(
        cls, discord.Color.greyple()
    )


class RiskCog(commands.Cog, name="Risk"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="scan", description="Generate a full risk intelligence report for a member.")
    @app_commands.describe(user="The member to analyze")
    async def scan(self, interaction: discord.Interaction, user: discord.Member):
        await interaction.response.defer(thinking=True)

        history = storage.get_guild_history(interaction.guild_id)
        result = scoring.calculate_risk(user, history)
        storage.save_scan_result(user.id, interaction.guild_id, result)

        avatar_bytes = None
        try:
            avatar_bytes = await user.display_avatar.replace(format="png", size=256).read()
        except Exception:
            pass

        card = generate_card(
            username=user.name,
            display_name=user.display_name,
            user_id=str(user.id),
            score=result["score"],
            classification=result["classification"],
            reasons=result["reasons"],
            account_age_days=result["details"]["account_age_days"],
            avatar_bytes=avatar_bytes,
        )
        file = discord.File(card, filename="analysis_card.png")
        top_reason = result["reasons"][0] if result["reasons"] else "No significant indicators detected."
        embed = discord.Embed(
            title="Analysis Complete",
            description=f"Risk scan completed for **{user.mention}**.\n*{top_reason}*",
            color=_risk_color(result["classification"]),
        )
        embed.set_image(url="attachment://analysis_card.png")
        embed.set_footer(text="NotHide — Results are probabilistic, not definitive.")
        await interaction.followup.send(embed=embed, file=file, view=AnalysisView(result, user))

    @app_commands.command(name="risk", description="Get a quick LOW/MEDIUM/HIGH risk classification for a member.")
    @app_commands.describe(user="The member to check")
    async def risk(self, interaction: discord.Interaction, user: discord.Member):
        await interaction.response.defer(thinking=True, ephemeral=True)

        history = storage.get_guild_history(interaction.guild_id)
        result = scoring.calculate_risk(user, history)

        cls = result["classification"]
        score = result["score"]
        cls_emoji = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🔴"}.get(cls, "⚪")

        embed = discord.Embed(
            title=f"Risk Classification — {user.display_name}",
            description=f"{cls_emoji} **{cls} RISK** — Score: `{score}/100`",
            color=_risk_color(cls),
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        if result["reasons"]:
            embed.add_field(
                name="Top Indicators",
                value="\n".join(f"` → ` {r}" for r in result["reasons"][:3]),
                inline=False,
            )
        embed.set_footer(text="Use /scan for the full report with visual analysis card.")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="altsuspect", description="Run alt account detection analysis on a member.")
    @app_commands.describe(user="The member to check for alt patterns")
    async def altsuspect(self, interaction: discord.Interaction, user: discord.Member):
        await interaction.response.defer(thinking=True)

        history = storage.get_guild_history(interaction.guild_id)
        result = scoring.calculate_risk(user, history)

        age_days = result["details"]["account_age_days"]
        sim_score = result["breakdown"]["behavioral"]
        cluster_score = result["breakdown"]["cluster"]
        alt_score = min(100, int((sim_score / 25 * 40) + (cluster_score / 26 * 35) + (min(30, max(0, 30 - age_days)) / 30 * 25)))

        if alt_score >= 60:
            verdict = "🔴 Likely Alt Account"
            verdict_color = discord.Color.red()
        elif alt_score >= 35:
            verdict = "🟡 Possible Alt — Investigate"
            verdict_color = discord.Color.yellow()
        else:
            verdict = "🟢 Unlikely to be an Alt"
            verdict_color = discord.Color.green()

        avatar_bytes = None
        try:
            avatar_bytes = await user.display_avatar.replace(format="png", size=256).read()
        except Exception:
            pass

        alt_reasons = [r for r in result["reasons"] if any(
            k in r.lower() for k in ["similar", "pattern", "cluster", "new", "created"]
        )]
        if not alt_reasons:
            alt_reasons = result["reasons"]

        card = generate_card(
            username=user.name,
            display_name=user.display_name,
            user_id=str(user.id),
            score=alt_score,
            classification="HIGH" if alt_score >= 60 else ("MEDIUM" if alt_score >= 35 else "LOW"),
            reasons=alt_reasons[:4] or ["No alt indicators detected."],
            account_age_days=age_days,
            avatar_bytes=avatar_bytes,
        )
        file = discord.File(card, filename="altsuspect.png")
        embed = discord.Embed(
            title="Alt Account Detection",
            description=f"**{verdict}**\nAlt Probability Score: `{alt_score}/100`\n\nScanned **{user.mention}** for alt account signals.",
            color=verdict_color,
        )
        embed.set_image(url="attachment://altsuspect.png")
        embed.add_field(name="Behavioral Score", value=f"`{sim_score}/25`", inline=True)
        embed.add_field(name="Cluster Score", value=f"`{cluster_score}/26`", inline=True)
        embed.add_field(name="Account Age", value=f"`{age_days}d`", inline=True)
        embed.set_footer(text="NotHide — Probabilistic analysis. Not a definitive verdict.")
        await interaction.followup.send(embed=embed, file=file)

    @app_commands.command(name="behavior", description="Analyze a member's behavioral patterns.")
    @app_commands.describe(user="The member to analyze")
    async def behavior(self, interaction: discord.Interaction, user: discord.Member):
        await interaction.response.defer(thinking=True, ephemeral=True)

        act = storage.get_user_activity(user.id, interaction.guild_id)
        history = storage.get_guild_history(interaction.guild_id)
        result = scoring.calculate_risk(user, history)
        total_msgs = act["total"]
        channels = act.get("channels", {})
        top_channel_id = max(channels, key=channels.get) if channels else None
        top_channel = interaction.guild.get_channel(int(top_channel_id)) if top_channel_id and interaction.guild else None

        embed = discord.Embed(
            title=f"Behavioral Analysis — {user.display_name}",
            color=discord.Color.blurple(),
        )
        embed.set_thumbnail(url=user.display_avatar.url)

        pattern_lines = []
        if result["breakdown"]["behavioral"] > 15:
            pattern_lines.append("⚠️ High username similarity to recent joins detected")
        if result["breakdown"]["cluster"] > 15:
            pattern_lines.append("⚠️ Join cluster anomaly — joined with a group")
        if total_msgs == 0:
            pattern_lines.append("⚠️ No tracked message activity (lurker behavior)")
        if not pattern_lines:
            pattern_lines.append("✅ No suspicious behavioral patterns detected")

        embed.add_field(name="Tracked Messages", value=f"`{total_msgs:,}`", inline=True)
        embed.add_field(
            name="Most Active In",
            value=f"{top_channel.mention if top_channel else 'Unknown'}",
            inline=True,
        )
        embed.add_field(
            name="Behavioral Risk Score",
            value=f"`{result['breakdown']['behavioral']}/25`",
            inline=True,
        )
        embed.add_field(
            name="Pattern Analysis",
            value="\n".join(pattern_lines),
            inline=False,
        )
        embed.set_footer(text="NotHide — Behavioral data collected since bot joined")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="trustscore", description="Calculate a reputation/trust score for a member.")
    @app_commands.describe(user="The member to evaluate")
    async def trustscore(self, interaction: discord.Interaction, user: discord.Member):
        await interaction.response.defer(thinking=True, ephemeral=True)

        history = storage.get_guild_history(interaction.guild_id)
        result = scoring.calculate_risk(user, history)
        warnings = storage.get_warnings(user.id, interaction.guild_id)
        flag = storage.get_flag(user.id, interaction.guild_id)
        act = storage.get_user_activity(user.id, interaction.guild_id)

        age_days = result["details"]["account_age_days"]
        tenure_days = (datetime.now(timezone.utc) - user.joined_at).days if user.joined_at else 0

        base = 100 - result["score"]
        age_bonus = min(15, age_days // 60)
        tenure_bonus = min(15, tenure_days // 30)
        warning_penalty = len(warnings) * 8
        flag_penalty = 20 if flag else 0
        boost_bonus = 5 if user.premium_since else 0
        activity_bonus = min(10, act["total"] // 50)

        trust = max(0, min(100, base + age_bonus + tenure_bonus + boost_bonus + activity_bonus - warning_penalty - flag_penalty))

        if trust >= 75:
            label, color, emoji = "HIGH TRUST", discord.Color.green(), "🟢"
        elif trust >= 45:
            label, color, emoji = "MODERATE TRUST", discord.Color.yellow(), "🟡"
        else:
            label, color, emoji = "LOW TRUST", discord.Color.red(), "🔴"

        embed = discord.Embed(
            title=f"Trust Score — {user.display_name}",
            description=f"{emoji} **{label}** — `{trust}/100`",
            color=color,
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(name="Base (from risk)", value=f"`{base}pts`", inline=True)
        embed.add_field(name="Age Bonus", value=f"`+{age_bonus}pts`", inline=True)
        embed.add_field(name="Tenure Bonus", value=f"`+{tenure_bonus}pts`", inline=True)
        embed.add_field(name="Warning Penalty", value=f"`-{warning_penalty}pts`", inline=True)
        embed.add_field(name="Flag Penalty", value=f"`-{flag_penalty}pts`", inline=True)
        embed.add_field(name="Activity Bonus", value=f"`+{activity_bonus}pts`", inline=True)
        embed.set_footer(text="Trust score is based on risk signals, server tenure, and moderation history.")
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(RiskCog(bot))
