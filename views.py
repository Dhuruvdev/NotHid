import discord
from scoring import explain_score

class AnalysisView(discord.ui.View):
    def __init__(self, scan_result: dict, member: discord.Member):
        super().__init__(timeout=300)
        self.scan_result = scan_result
        self.member = member

    @discord.ui.button(label="View Details", style=discord.ButtonStyle.secondary, emoji="🔍", custom_id="view_details")
    async def view_details(self, interaction: discord.Interaction, button: discord.ui.Button):
        bd = self.scan_result["breakdown"]
        score = self.scan_result["score"]
        cls = self.scan_result["classification"]
        details = self.scan_result.get("details", {})
        age = details.get("account_age_days", "?")

        cls_colors = {"LOW": discord.Color.green(), "MEDIUM": discord.Color.yellow(), "HIGH": discord.Color.red()}
        color = cls_colors.get(cls, discord.Color.greyple())

        embed = discord.Embed(
            title=f"Detailed Analysis — {self.member.display_name}",
            color=color,
        )
        embed.set_thumbnail(url=self.member.display_avatar.url)

        score_bar = _build_score_bar(score)
        embed.add_field(
            name="Risk Score",
            value=f"```{score_bar}```\n**{score}/100** — `{cls} RISK`",
            inline=False,
        )

        embed.add_field(
            name="Score Breakdown",
            value=(
                f"```\n"
                f"Static signals    {bd['static']:>3}pts\n"
                f"  Account age     ·  Based on {age}d account\n"
                f"  Username        ·  Pattern & structure\n"
                f"\n"
                f"Behavioral        {bd['behavioral']:>3}pts\n"
                f"  Similarity      ·  Recent member comparison\n"
                f"\n"
                f"Cluster detection {bd['cluster']:>3}pts\n"
                f"  Join timing     ·  Last 50 joins analyzed\n"
                f"```"
            ),
            inline=False,
        )

        signals = self.scan_result.get("reasons", [])
        if signals:
            embed.add_field(
                name="Risk Indicators",
                value="\n".join(f"` ➤ ` {r}" for r in signals),
                inline=False,
            )

        embed.set_footer(text="Cybork — Probabilistic risk analysis. Not a definitive verdict.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Why this score?", style=discord.ButtonStyle.secondary, emoji="❓", custom_id="why_score")
    async def why_score(self, interaction: discord.Interaction, button: discord.ui.Button):
        explanation = explain_score(self.scan_result)
        embed = discord.Embed(
            title="Score Explanation",
            description=explanation,
            color=discord.Color.blurple(),
        )
        embed.set_footer(text="Cybork uses probabilistic signals — not accusations.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Enable Auto Detection ⚡", style=discord.ButtonStyle.primary, custom_id="premium")
    async def premium_feature(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="⚡ Auto Detection — Premium Feature",
            description=(
                "**Auto Detection** continuously monitors new joins and flags suspicious patterns in real-time.\n\n"
                "**Includes:**\n"
                "` → ` Automatic scan on every new member join\n"
                "` → ` Cluster detection with instant alerts\n"
                "` → ` Custom threshold configuration\n"
                "` → ` Audit log integration\n"
                "` → ` Role-based auto-actions\n\n"
                "*Upgrade to Cybork Premium to unlock this feature.*"
            ),
            color=discord.Color.og_blurple(),
        )
        embed.set_footer(text="Cybork Premium — Coming Soon")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

def _build_score_bar(score: int, width: int = 20) -> str:
    filled = round((score / 100) * width)
    bar = "█" * filled + "░" * (width - filled)
    return f"{bar}  {score}%"
