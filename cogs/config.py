import discord
from discord.ext import commands
from discord import app_commands

import storage


def _config_embed(guild: discord.Guild, cfg: dict) -> discord.Embed:
    def ch(channel_id):
        if not channel_id:
            return "`Not set`"
        c = guild.get_channel(int(channel_id))
        return c.mention if c else "`Invalid channel`"

    def role(role_id):
        if not role_id:
            return "`Not set`"
        r = guild.get_role(int(role_id))
        return r.mention if r else "`Invalid role`"

    def tog(val):
        return "✅ Enabled" if val else "❌ Disabled"

    embed = discord.Embed(title=f"Cybork Configuration — {guild.name}", color=discord.Color.blurple())
    embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
    embed.add_field(name="📋 Mod Log Channel", value=ch(cfg["mod_log_channel"]), inline=True)
    embed.add_field(name="🔔 Alerts Channel", value=ch(cfg["alerts_channel"]), inline=True)
    embed.add_field(name="🎭 Auto Role", value=role(cfg["autorole"]), inline=True)
    embed.add_field(name="🛡️ Anti-Spam", value=tog(cfg["antispam"]), inline=True)
    embed.add_field(name="🔗 Anti-Link", value=tog(cfg["antilink"]), inline=True)
    embed.add_field(name="🔡 Caps Filter", value=tog(cfg["capsfilter"]), inline=True)
    embed.add_field(name="⚡ Risk Alerts", value=tog(cfg["risk_alerts"]), inline=True)
    embed.add_field(name="📊 Activity Alerts", value=tog(cfg["activity_alerts"]), inline=True)
    embed.add_field(name="🚨 Spam Alerts", value=tog(cfg["spam_alerts"]), inline=True)
    autokick = f"`{cfg['autokick_days']}d inactive`" if cfg["autokick_days"] else "❌ Disabled"
    embed.add_field(name="⏰ Auto-Kick", value=autokick, inline=True)
    embed.add_field(name="⚠️ Auto-Warn Spam", value=tog(cfg["autowarn_spam"]), inline=True)
    embed.set_footer(text="Use >setmodlog, >setalerts to configure channels.")
    return embed


class ConfigCog(commands.Cog, name="Config"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ── Slash Commands ────────────────────────────────────────────────────────

    @app_commands.command(name="setup", description="View the current server configuration for Cybork.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def setup(self, interaction: discord.Interaction):
        cfg = storage.get_server_config(interaction.guild_id)
        embed = _config_embed(interaction.guild, cfg)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="setmodlog", description="Set the channel where moderation logs are posted.")
    @app_commands.describe(channel="The channel for mod logs")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def setmodlog(self, interaction: discord.Interaction, channel: discord.TextChannel):
        storage.set_server_config(interaction.guild_id, mod_log_channel=str(channel.id))
        embed = discord.Embed(description=f"✅ Mod log channel set to {channel.mention}.", color=discord.Color.green())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="setalerts", description="Set the channel where Cybork alerts are posted.")
    @app_commands.describe(channel="The channel for alerts")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def setalerts(self, interaction: discord.Interaction, channel: discord.TextChannel):
        storage.set_server_config(interaction.guild_id, alerts_channel=str(channel.id))
        embed = discord.Embed(description=f"✅ Alerts channel set to {channel.mention}.", color=discord.Color.green())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ── Prefix Commands ───────────────────────────────────────────────────────

    @commands.command(name="setup")
    @commands.has_permissions(manage_guild=True)
    async def setup_prefix(self, ctx: commands.Context):
        cfg = storage.get_server_config(ctx.guild.id)
        embed = _config_embed(ctx.guild, cfg)
        await ctx.reply(embed=embed, mention_author=False)

    @commands.command(name="setmodlog")
    @commands.has_permissions(manage_guild=True)
    async def setmodlog_prefix(self, ctx: commands.Context, channel: discord.TextChannel):
        storage.set_server_config(ctx.guild.id, mod_log_channel=str(channel.id))
        embed = discord.Embed(description=f"✅ Mod log channel set to {channel.mention}.", color=discord.Color.green())
        await ctx.reply(embed=embed, mention_author=False)

    @commands.command(name="setalerts")
    @commands.has_permissions(manage_guild=True)
    async def setalerts_prefix(self, ctx: commands.Context, channel: discord.TextChannel):
        storage.set_server_config(ctx.guild.id, alerts_channel=str(channel.id))
        embed = discord.Embed(description=f"✅ Alerts channel set to {channel.mention}.", color=discord.Color.green())
        await ctx.reply(embed=embed, mention_author=False)

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("❌ You need `Manage Server` permission.", ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ Error: `{error}`", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(ConfigCog(bot))
