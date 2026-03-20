import discord
from discord.ext import commands
from discord import app_commands

import storage
import emojis_loader as E

WHITE = discord.Color.from_rgb(255, 255, 255)


def _parse_bool(value: str):
    if value.lower() in ("on", "true", "yes", "enable", "1"):
        return True
    if value.lower() in ("off", "false", "no", "disable", "0"):
        return False
    return None


class AlertsCog(commands.Cog, name="Alerts"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    alerts_group = app_commands.Group(
        name="alerts",
        description="Configure Cybork alert notifications.",
    )

    # ── Slash Commands ────────────────────────────────────────────────────────

    @alerts_group.command(name="risk", description="Toggle risk alerts for high-score joins.")
    @app_commands.describe(enabled="Turn on or off")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def alerts_risk(self, interaction: discord.Interaction, enabled: bool):
        cfg = storage.get_server_config(interaction.guild_id)
        if enabled and not cfg.get("alerts_channel"):
            await interaction.response.send_message(
                f"{E.get('error', '❌')} Set an alerts channel first with `>setalerts #channel`.", ephemeral=True
            )
            return
        storage.set_server_config(interaction.guild_id, risk_alerts=enabled)
        icon = E.get("success", "✅") if enabled else E.get("error", "❌")
        state = "enabled" if enabled else "disabled"
        embed = discord.Embed(
            title=f"{E.get('alert', '🚨')} Risk Alerts",
            description=f"High-risk join alerts are now **{state}** {icon}.",
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
                f"{E.get('error', '❌')} Set an alerts channel first with `>setalerts #channel`.", ephemeral=True
            )
            return
        storage.set_server_config(interaction.guild_id, activity_alerts=enabled)
        icon = E.get("success", "✅") if enabled else E.get("error", "❌")
        state = "enabled" if enabled else "disabled"
        embed = discord.Embed(
            title=f"{E.get('chart', '📈')} Activity Alerts",
            description=f"Activity spike alerts are now **{state}** {icon}.",
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
                f"{E.get('error', '❌')} Set an alerts channel first with `>setalerts #channel`.", ephemeral=True
            )
            return
        storage.set_server_config(interaction.guild_id, spam_alerts=enabled)
        icon = E.get("success", "✅") if enabled else E.get("error", "❌")
        state = "enabled" if enabled else "disabled"
        embed = discord.Embed(
            title=f"{E.get('alert', '🚨')} Spam Alerts",
            description=f"Spam detection alerts are now **{state}** {icon}.",
            color=discord.Color.green() if enabled else discord.Color.red(),
        )
        await interaction.response.send_message(embed=embed)

    @alerts_group.command(name="status", description="View current alert configuration.")
    async def alerts_status(self, interaction: discord.Interaction):
        cfg = storage.get_server_config(interaction.guild_id)
        ch_id = cfg.get("alerts_channel")
        ch = interaction.guild.get_channel(int(ch_id)) if ch_id else None

        def tog(v):
            return f"{E.get('success', '✅')} On" if v else f"{E.get('error', '❌')} Off"

        embed = discord.Embed(title=f"{E.get('bell', '🔔')} Alert Configuration", color=WHITE)
        embed.add_field(name=f"{E.get('announcement', '📢')} Alerts Channel", value=ch.mention if ch else "`Not set`",  inline=False)
        embed.add_field(name=f"{E.get('warning', '⚠️')} Risk Alerts",         value=tog(cfg["risk_alerts"]),            inline=True)
        embed.add_field(name=f"{E.get('activity', '📊')} Activity Alerts",    value=tog(cfg["activity_alerts"]),        inline=True)
        embed.add_field(name=f"{E.get('alert', '🚨')} Spam Alerts",           value=tog(cfg["spam_alerts"]),            inline=True)
        embed.set_footer(text="Use >setalerts to set the alert channel.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ── Prefix Commands ───────────────────────────────────────────────────────

    @commands.command(name="alertsrisk")
    @commands.has_permissions(manage_guild=True)
    async def alertsrisk_prefix(self, ctx: commands.Context, toggle: str):
        enabled = _parse_bool(toggle)
        if enabled is None:
            await ctx.reply(f"{E.get('error', '❌')} Use `on` or `off`.", mention_author=False)
            return
        cfg = storage.get_server_config(ctx.guild.id)
        if enabled and not cfg.get("alerts_channel"):
            await ctx.reply(f"{E.get('error', '❌')} Set an alerts channel first with `>setalerts #channel`.", mention_author=False)
            return
        storage.set_server_config(ctx.guild.id, risk_alerts=enabled)
        icon = E.get("success", "✅") if enabled else E.get("error", "❌")
        state = "enabled" if enabled else "disabled"
        embed = discord.Embed(
            title=f"{E.get('alert', '🚨')} Risk Alerts",
            description=f"High-risk join alerts are now **{state}** {icon}.",
            color=discord.Color.green() if enabled else discord.Color.red(),
        )
        await ctx.reply(embed=embed, mention_author=False)

    @commands.command(name="alertsactivity")
    @commands.has_permissions(manage_guild=True)
    async def alertsactivity_prefix(self, ctx: commands.Context, toggle: str):
        enabled = _parse_bool(toggle)
        if enabled is None:
            await ctx.reply(f"{E.get('error', '❌')} Use `on` or `off`.", mention_author=False)
            return
        cfg = storage.get_server_config(ctx.guild.id)
        if enabled and not cfg.get("alerts_channel"):
            await ctx.reply(f"{E.get('error', '❌')} Set an alerts channel first with `>setalerts #channel`.", mention_author=False)
            return
        storage.set_server_config(ctx.guild.id, activity_alerts=enabled)
        icon = E.get("success", "✅") if enabled else E.get("error", "❌")
        state = "enabled" if enabled else "disabled"
        embed = discord.Embed(
            title=f"{E.get('chart', '📈')} Activity Alerts",
            description=f"Activity spike alerts are now **{state}** {icon}.",
            color=discord.Color.green() if enabled else discord.Color.red(),
        )
        await ctx.reply(embed=embed, mention_author=False)

    @commands.command(name="alertsspam")
    @commands.has_permissions(manage_guild=True)
    async def alertsspam_prefix(self, ctx: commands.Context, toggle: str):
        enabled = _parse_bool(toggle)
        if enabled is None:
            await ctx.reply(f"{E.get('error', '❌')} Use `on` or `off`.", mention_author=False)
            return
        cfg = storage.get_server_config(ctx.guild.id)
        if enabled and not cfg.get("alerts_channel"):
            await ctx.reply(f"{E.get('error', '❌')} Set an alerts channel first with `>setalerts #channel`.", mention_author=False)
            return
        storage.set_server_config(ctx.guild.id, spam_alerts=enabled)
        icon = E.get("success", "✅") if enabled else E.get("error", "❌")
        state = "enabled" if enabled else "disabled"
        embed = discord.Embed(
            title=f"{E.get('alert', '🚨')} Spam Alerts",
            description=f"Spam detection alerts are now **{state}** {icon}.",
            color=discord.Color.green() if enabled else discord.Color.red(),
        )
        await ctx.reply(embed=embed, mention_author=False)

    @commands.command(name="alertsstatus")
    async def alertsstatus_prefix(self, ctx: commands.Context):
        cfg = storage.get_server_config(ctx.guild.id)
        ch_id = cfg.get("alerts_channel")
        ch = ctx.guild.get_channel(int(ch_id)) if ch_id else None

        def tog(v):
            return f"{E.get('success', '✅')} On" if v else f"{E.get('error', '❌')} Off"

        embed = discord.Embed(title=f"{E.get('bell', '🔔')} Alert Configuration", color=WHITE)
        embed.add_field(name=f"{E.get('announcement', '📢')} Alerts Channel", value=ch.mention if ch else "`Not set`", inline=False)
        embed.add_field(name=f"{E.get('warning', '⚠️')} Risk Alerts",         value=tog(cfg["risk_alerts"]),           inline=True)
        embed.add_field(name=f"{E.get('activity', '📊')} Activity Alerts",    value=tog(cfg["activity_alerts"]),       inline=True)
        embed.add_field(name=f"{E.get('alert', '🚨')} Spam Alerts",           value=tog(cfg["spam_alerts"]),           inline=True)
        embed.set_footer(text="Use >setalerts to set the alert channel.")
        await ctx.reply(embed=embed, mention_author=False)

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(f"{E.get('error', '❌')} You need `Manage Server` permission.", ephemeral=True)
        else:
            await interaction.response.send_message(f"{E.get('error', '❌')} Error: `{error}`", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(AlertsCog(bot))
