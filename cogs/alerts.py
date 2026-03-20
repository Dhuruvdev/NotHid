import discord
from discord.ext import commands
from discord import app_commands

import storage


class AlertsCog(commands.Cog, name="Alerts"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    alerts_group = app_commands.Group(
        name="alerts",
        description="Configure Cybork alert notifications.",
    )

    @alerts_group.command(name="risk", description="Toggle risk alerts for high-score joins.")
    @app_commands.describe(enabled="Turn on or off")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def alerts_risk(self, interaction: discord.Interaction, enabled: bool):
        cfg = storage.get_server_config(interaction.guild_id)
        if enabled and not cfg.get("alerts_channel"):
            await interaction.response.send_message(
                "❌ Set an alerts channel first with `/setalerts #channel`.", ephemeral=True
            )
            return
        storage.set_server_config(interaction.guild_id, risk_alerts=enabled)
        state = "enabled ✅" if enabled else "disabled ❌"
        embed = discord.Embed(
            title="Risk Alerts",
            description=f"High-risk join alerts are now **{state}**.",
            color=discord.Color.green() if enabled else discord.Color.red(),
        )
        await interaction.response.send_message(embed=embed)

    @alerts_group.command(name="activity", description="Toggle alerts for unusual activity spikes.")
    @app_commands.describe(enabled="Turn on or off")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def alerts_activity(self, interaction: discord.Interaction, enabled: bool):
        cfg = storage.get_server_config(interaction.guild_id)
        if enabled and not cfg.get("alerts_channel"):
            await interaction.response.send_message(
                "❌ Set an alerts channel first with `/setalerts #channel`.", ephemeral=True
            )
            return
        storage.set_server_config(interaction.guild_id, activity_alerts=enabled)
        state = "enabled ✅" if enabled else "disabled ❌"
        embed = discord.Embed(
            title="Activity Alerts",
            description=f"Activity spike alerts are now **{state}**.",
            color=discord.Color.green() if enabled else discord.Color.red(),
        )
        await interaction.response.send_message(embed=embed)

    @alerts_group.command(name="spam", description="Toggle alerts when spam is detected.")
    @app_commands.describe(enabled="Turn on or off")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def alerts_spam(self, interaction: discord.Interaction, enabled: bool):
        cfg = storage.get_server_config(interaction.guild_id)
        if enabled and not cfg.get("alerts_channel"):
            await interaction.response.send_message(
                "❌ Set an alerts channel first with `/setalerts #channel`.", ephemeral=True
            )
            return
        storage.set_server_config(interaction.guild_id, spam_alerts=enabled)
        state = "enabled ✅" if enabled else "disabled ❌"
        embed = discord.Embed(
            title="Spam Alerts",
            description=f"Spam detection alerts are now **{state}**.",
            color=discord.Color.green() if enabled else discord.Color.red(),
        )
        await interaction.response.send_message(embed=embed)

    @alerts_group.command(name="status", description="View current alert configuration.")
    async def alerts_status(self, interaction: discord.Interaction):
        cfg = storage.get_server_config(interaction.guild_id)
        ch_id = cfg.get("alerts_channel")
        ch = interaction.guild.get_channel(int(ch_id)) if ch_id else None

        def tog(v):
            return "✅ On" if v else "❌ Off"

        embed = discord.Embed(title="Alert Configuration", color=discord.Color.blurple())
        embed.add_field(name="📢 Alerts Channel", value=ch.mention if ch else "`Not set`", inline=False)
        embed.add_field(name="⚠️ Risk Alerts", value=tog(cfg["risk_alerts"]), inline=True)
        embed.add_field(name="📊 Activity Alerts", value=tog(cfg["activity_alerts"]), inline=True)
        embed.add_field(name="🚨 Spam Alerts", value=tog(cfg["spam_alerts"]), inline=True)
        embed.set_footer(text="Use /setalerts to set the alert channel.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("❌ You need `Manage Server` permission.", ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ Error: `{error}`", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(AlertsCog(bot))
