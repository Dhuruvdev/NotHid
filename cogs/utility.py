import discord
from discord.ext import commands
from discord import app_commands
from help_view import HelpMenuView


class UtilityCog(commands.Cog, name="Utility"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="ping", description="Check the bot's response latency.")
    async def ping(self, interaction: discord.Interaction):
        latency_ms = round(self.bot.latency * 1000)
        embed = discord.Embed(
            title="Latency Check",
            description=f"WebSocket latency: `{latency_ms}ms`",
            color=discord.Color.blurple(),
        )
        embed.set_footer(text="Cybork")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="about", description="Learn about Cybork and what it does.")
    async def about(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="About Cybork",
            description=(
                "**Cybork** is a risk intelligence tool for Discord servers.\n\n"
                "It analyzes members using multiple signal layers:\n"
                "` → ` **Static signals** — Account age, username structure\n"
                "` → ` **Behavioral similarity** — Pattern matching with recent joins\n"
                "` → ` **Cluster detection** — Join timing anomaly detection\n\n"
                "Results are *probabilistic* and should be used as indicators, not verdicts.\n\n"
                "Use `/help` to view all available commands."
            ),
            color=discord.Color.og_blurple(),
        )
        embed.set_footer(text="Cybork — Detect What Others Miss")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="help", description="Browse all Cybork commands in an interactive menu.")
    async def help(self, interaction: discord.Interaction):
        await interaction.response.send_message(view=HelpMenuView())


async def setup(bot: commands.Bot):
    await bot.add_cog(UtilityCog(bot))
