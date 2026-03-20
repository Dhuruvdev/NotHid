import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timezone
from typing import Optional

import storage


def _ts(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso)
        return f"<t:{int(dt.timestamp())}:R>"
    except Exception:
        return iso


class HistoryCog(commands.Cog, name="History"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="warnings", description="View all warnings for a member.")
    @app_commands.describe(user="The member to check")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def warnings(self, interaction: discord.Interaction, user: discord.Member):
        warns = storage.get_warnings(user.id, interaction.guild_id)

        embed = discord.Embed(
            title=f"Warnings — {user.display_name}",
            color=discord.Color.yellow(),
        )
        embed.set_thumbnail(url=user.display_avatar.url)

        if not warns:
            embed.description = "✅ This member has no warnings."
        else:
            embed.description = f"**{len(warns)} warning(s) on record.**"
            for i, w in enumerate(warns[-10:], 1):
                mod_id = w.get("moderator_id", "Unknown")
                embed.add_field(
                    name=f"#{i} — ID: `{w['id']}`",
                    value=f"**Reason:** {w['reason']}\n**By:** <@{mod_id}> · {_ts(w['timestamp'])}",
                    inline=False,
                )
        embed.set_footer(text="Use /warn to add · Remove a specific ID with /history clear")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="history", description="View the moderation history for a member.")
    @app_commands.describe(user="The member to view")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def history(self, interaction: discord.Interaction, user: discord.Member):
        actions = storage.get_mod_history(user.id, interaction.guild_id)
        warns = storage.get_warnings(user.id, interaction.guild_id)

        embed = discord.Embed(
            title=f"Mod History — {user.display_name}",
            color=discord.Color.blurple(),
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(name="Total Warnings", value=f"`{len(warns)}`", inline=True)
        embed.add_field(name="Total Actions", value=f"`{len(actions)}`", inline=True)

        action_emoji = {"WARN": "⚠️", "MUTE": "🔇", "KICK": "👢", "BAN": "🔨"}

        if not actions:
            embed.description = "✅ No moderation actions recorded."
        else:
            lines = []
            for a in actions[-10:]:
                emoji = action_emoji.get(a["action"], "•")
                mod = f"<@{a['moderator_id']}>"
                lines.append(f"{emoji} **{a['action']}** by {mod} — {_ts(a['timestamp'])}\n` ` {a['reason']}")
            embed.description = "\n\n".join(lines)

        embed.set_footer(text="Showing last 10 actions")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="notes", description="View or add private moderator notes for a member.")
    @app_commands.describe(user="Target member", note="Add a new note (leave empty to view existing notes)")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def notes(self, interaction: discord.Interaction, user: discord.Member, note: Optional[str] = None):
        if note:
            entry = storage.add_note(user.id, interaction.guild_id, note, interaction.user.id)
            embed = discord.Embed(
                title="Note Added",
                description=f"Note `{entry['id']}` saved for **{user.display_name}**.\n\n> {note}",
                color=discord.Color.blurple(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            existing = storage.get_notes(user.id, interaction.guild_id)
            embed = discord.Embed(
                title=f"Mod Notes — {user.display_name}",
                color=discord.Color.blurple(),
            )
            embed.set_thumbnail(url=user.display_avatar.url)
            if not existing:
                embed.description = "No notes on file for this member."
            else:
                lines = []
                for n in existing[-8:]:
                    lines.append(f"`{n['id']}` · <@{n['author_id']}> {_ts(n['timestamp'])}\n> {n['note']}")
                embed.description = "\n\n".join(lines)
            embed.set_footer(text="Notes are private — only moderators can see them.")
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="flag", description="Manually flag a member as suspicious.")
    @app_commands.describe(user="The member to flag", reason="Reason for flagging")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def flag(self, interaction: discord.Interaction, user: discord.Member, reason: str = "Manually flagged"):
        storage.flag_user(user.id, interaction.guild_id, reason, interaction.user.id)
        embed = discord.Embed(
            title="🚩 Member Flagged",
            description=f"**{user.mention}** has been flagged as suspicious.\n**Reason:** {reason}",
            color=discord.Color.orange(),
        )
        embed.set_footer(text="Use /unflag to remove the flag.")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="unflag", description="Remove the suspicious flag from a member.")
    @app_commands.describe(user="The member to unflag")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def unflag(self, interaction: discord.Interaction, user: discord.Member):
        removed = storage.unflag_user(user.id, interaction.guild_id)
        if removed:
            embed = discord.Embed(
                title="✅ Flag Removed",
                description=f"The flag on **{user.mention}** has been removed.",
                color=discord.Color.green(),
            )
        else:
            embed = discord.Embed(
                title="Not Flagged",
                description=f"**{user.mention}** is not currently flagged.",
                color=discord.Color.greyple(),
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("❌ You need `Moderate Members` permission.", ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ Error: `{error}`", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(HistoryCog(bot))
