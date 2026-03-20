import os
import logging
import discord
from discord.ext import commands
from discord import app_commands

import storage
import scoring
from image_generator import generate_card
from views import AnalysisView
from help_view import HelpMenuView

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("nothide")

TOKEN = os.environ.get("DISCORD_TOKEN")
if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN environment variable is not set.")

GUILD_ID = os.environ.get("GUILD_ID")

intents = discord.Intents.default()
intents.members = True
intents.message_content = False


class NotHideBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=commands.when_mentioned, intents=intents, help_command=None)

    async def setup_hook(self):
        self.tree.add_command(scan_command)
        self.tree.add_command(ping_command)
        self.tree.add_command(about_command)
        self.tree.add_command(help_command)

        if GUILD_ID:
            guild_obj = discord.Object(id=int(GUILD_ID))
            self.tree.copy_global_to(guild=guild_obj)
            await self.tree.sync(guild=guild_obj)
            log.info(f"Commands synced to guild {GUILD_ID} (instant)")
        else:
            await self.tree.sync()
            log.info("Commands synced globally (may take up to 1 hour to propagate)")

    async def on_ready(self):
        log.info(f"NotHide online — logged in as {self.user} ({self.user.id})")
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="for suspicious patterns",
            )
        )

    async def on_member_join(self, member: discord.Member):
        storage.record_join(member.id, member.name, member.guild.id, member.created_at)
        log.info(f"Recorded join: {member.name} ({member.id}) in guild {member.guild.id}")


bot = NotHideBot()


@app_commands.command(name="scan", description="Analyze a server member and generate a risk intelligence report.")
@app_commands.describe(user="The member to analyze")
async def scan_command(interaction: discord.Interaction, user: discord.Member):
    await interaction.response.defer(thinking=True)

    guild_history = storage.get_guild_history(interaction.guild_id)
    result = scoring.calculate_risk(user, guild_history)
    storage.save_scan_result(user.id, interaction.guild_id, result)

    avatar_bytes = None
    try:
        avatar_bytes = await user.display_avatar.replace(format="png", size=256).read()
    except Exception as e:
        log.warning(f"Could not fetch avatar for {user.name}: {e}")

    card_buffer = generate_card(
        username=user.name,
        display_name=user.display_name,
        user_id=str(user.id),
        score=result["score"],
        classification=result["classification"],
        reasons=result["reasons"],
        account_age_days=result["details"]["account_age_days"],
        avatar_bytes=avatar_bytes,
    )

    file = discord.File(card_buffer, filename="analysis_card.png")

    cls = result["classification"]
    cls_colors = {
        "LOW": discord.Color.green(),
        "MEDIUM": discord.Color.yellow(),
        "HIGH": discord.Color.red(),
    }
    color = cls_colors.get(cls, discord.Color.greyple())

    top_reason = result["reasons"][0] if result["reasons"] else "No significant indicators detected."

    embed = discord.Embed(
        title="Analysis Complete",
        description=(
            f"Risk scan completed for **{user.mention}**.\n"
            f"*{top_reason}*"
        ),
        color=color,
    )
    embed.set_image(url="attachment://analysis_card.png")
    embed.set_footer(text="NotHide — Detect What Others Miss  ·  Results are probabilistic, not definitive.")

    view = AnalysisView(scan_result=result, member=user)
    await interaction.followup.send(embed=embed, file=file, view=view)


@app_commands.command(name="ping", description="Check the bot's response latency.")
async def ping_command(interaction: discord.Interaction):
    latency_ms = round(bot.latency * 1000)
    embed = discord.Embed(
        title="Latency Check",
        description=f"WebSocket latency: `{latency_ms}ms`",
        color=discord.Color.blurple(),
    )
    embed.set_footer(text="NotHide")
    await interaction.response.send_message(embed=embed, ephemeral=True)


@app_commands.command(name="about", description="Learn about NotHide and what it does.")
async def about_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="About NotHide",
        description=(
            "**NotHide** is a risk intelligence tool for Discord servers.\n\n"
            "It analyzes members using multiple signal layers:\n"
            "` → ` **Static signals** — Account age, username structure\n"
            "` → ` **Behavioral similarity** — Pattern matching with recent joins\n"
            "` → ` **Cluster detection** — Join timing anomaly detection\n\n"
            "Results are *probabilistic* and should be used as indicators, not verdicts.\n\n"
            "**Commands:**\n"
            "`/scan` — Analyze a member's risk profile\n"
            "`/ping` — Check bot latency\n"
            "`/about` — This message"
        ),
        color=discord.Color.og_blurple(),
    )
    embed.set_footer(text="NotHide — Detect What Others Miss")
    await interaction.response.send_message(embed=embed, ephemeral=True)


@app_commands.command(name="help", description="Browse all NotHide commands in an interactive menu.")
async def help_command(interaction: discord.Interaction):
    await interaction.response.send_message(view=HelpMenuView())


if __name__ == "__main__":
    bot.run(TOKEN, log_handler=None)
