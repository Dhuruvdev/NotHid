import discord
import emojis_loader as E

WHITE = discord.Color.from_rgb(255, 255, 255)

COMMANDS_DATA = {
    "scan": {
        "label": "Scan & Risk",
        "emoji": E.get("scan", "🔍"),
        "description": "Risk intelligence commands",
        "commands": [
            (">scan @member",       "Full risk intelligence report with visual card"),
            (">risk @member",       "Quick LOW/MEDIUM/HIGH classification"),
            (">altsuspect @member", "Alt account detection analysis"),
            (">behavior @member",   "Behavioral pattern analysis"),
            (">trustscore @member", "Reputation and trust score"),
        ],
    },
    "moderation": {
        "label": "Moderation",
        "emoji": E.get("shield", "🛡️"),
        "description": "Server moderation commands",
        "perms_note": "Requires Moderate Members / Kick / Ban permissions.",
        "commands": [
            (">warn @member [reason]",           "Issue a warning — requires Moderate Members"),
            (">mute @member <duration> [reason]", "Timeout a member — requires Moderate Members"),
            (">kick @member [reason]",            "Kick a member — requires Kick Members"),
            (">ban @member [reason]",             "Ban a member — requires Ban Members"),
            (">lock [#channel] [reason]",         "Lock a channel — requires Manage Channels"),
            (">unlock [#channel] [reason]",       "Unlock a channel — requires Manage Channels"),
            (">slowmode <seconds> [#channel]",    "Set slowmode — requires Manage Channels"),
            (">antispam <on/off>",                "Toggle anti-spam — requires Manage Server"),
            (">antilink <on/off>",                "Toggle anti-link — requires Manage Server"),
            (">capsfilter <on/off>",              "Toggle caps filter — requires Manage Server"),
        ],
    },
    "history": {
        "label": "History & Flags",
        "emoji": E.get("note", "📋"),
        "description": "Moderation history and flagging",
        "perms_note": "Requires Moderate Members permission.",
        "commands": [
            (">warnings @member",      "View all warnings — requires Moderate Members"),
            (">history @member",       "Full moderation action history — requires Moderate Members"),
            (">notes @member [note]",  "View or add private mod notes — requires Moderate Members"),
            (">flag @member [reason]", "Flag a member as suspicious — requires Moderate Members"),
            (">unflag @member",        "Remove suspicious flag — requires Moderate Members"),
        ],
    },
    "analytics": {
        "label": "Analytics",
        "emoji": E.get("stats", "📊"),
        "description": "Server analytics and activity",
        "commands": [
            (">serverstats",       "Overall server statistics"),
            (">topusers",          "Most active members"),
            (">inactive",          "Members with no activity"),
            (">channels",          "Channel activity overview"),
            (">report",            "Full server health report — requires Manage Server"),
            (">profile @member",   "Member profile card"),
            (">activity @member",  "Member activity report"),
        ],
    },
    "config": {
        "label": "Configuration",
        "emoji": E.get("gear", "⚙️"),
        "description": "Bot and server configuration",
        "perms_note": "Requires Manage Server permission.",
        "commands": [
            (">setup",                "View current server configuration — requires Manage Server"),
            (">setmodlog #channel",   "Set moderation log channel — requires Manage Server"),
            (">setalerts #channel",   "Set alerts channel — requires Manage Server"),
            (">alertsrisk <on/off>",  "Toggle risk join alerts — requires Manage Server"),
            (">autoroleset @role",    "Set auto-role on join — requires Manage Roles"),
            (">autokickset <days>",   "Set inactive member auto-kick threshold — requires Kick Members"),
            (">autowarnspam <on/off>","Toggle auto-warn for spam — requires Manage Server"),
        ],
    },
    "utility": {
        "label": "Utility",
        "emoji": E.get("bot", "🤖"),
        "description": "General utility commands",
        "commands": [
            (">ping",           "Check bot latency"),
            (">about",          "About Cybork"),
            (">help",           "This command menu"),
            (">botinfo",        "Detailed bot information"),
            (">alertsstatus",   "View alert configuration"),
            (">autorolestatus", "View auto-role configuration"),
        ],
    },
}

OWNER_COMMANDS_DATA = {
    "owner": {
        "label": "Owner",
        "emoji": E.get("owner", "🔐"),
        "description": "Bot owner exclusive commands",
        "commands": [
            ("np @member",                       "No-prefix owner member lookup panel"),
            ("/sync [guild/global]",             "Sync slash commands to guild or globally"),
            ("/reload <cog/all>",                "Reload a cog extension"),
            ("/status <text> [kind]",            "Change bot activity status"),
            ("/botinfo",                         "Detailed bot statistics panel"),
            ("/announce <#channel> <message>",   "Send an announcement embed"),
            ("/shutdown",                        "Gracefully shut down the bot"),
            (">setowner [user_id]",              "Set bot owner ID in config.json"),
            (">setguild [guild_id]",             "Set guild ID for instant slash sync"),
            (">setsupport <invite_url>",         "Set support server invite URL"),
        ],
    },
}

PER_PAGE = 6


def _build_command_lines(cmds: list[tuple]) -> str:
    return "\n".join(f"• `{cmd}` — {desc}" for cmd, desc in cmds) or "*No commands found.*"


def _merged_data(is_owner: bool) -> dict:
    if is_owner:
        return {**COMMANDS_DATA, **OWNER_COMMANDS_DATA}
    return COMMANDS_DATA


class CategoryView(discord.ui.LayoutView):
    def __init__(
        self,
        category: str = "all",
        page: int = 1,
        is_owner: bool = False,
        owner_name: str | None = None,
        owner_id: int | None = None,
        support_invite: str | None = None,
    ):
        super().__init__(timeout=300)
        self.category = category
        self.page = page
        self._is_owner = is_owner
        self._owner_name = owner_name
        self._owner_id = owner_id
        self._support_invite = support_invite

        merged = _merged_data(is_owner)

        if category == "all":
            cat_label = "All Commands"
            cat_emoji = E.get("note", "📋")
            cmds = [
                (cmd, desc)
                for cat in merged.values()
                for cmd, desc in cat["commands"]
            ]
            perms_note = ""
        else:
            data = merged[category]
            cat_label = data["label"]
            cat_emoji = data["emoji"]
            cmds = data["commands"]
            perms_note = data.get("perms_note", "")

        total_pages = max(1, (len(cmds) + PER_PAGE - 1) // PER_PAGE)
        page_cmds = cmds[(page - 1) * PER_PAGE: page * PER_PAGE]
        cmd_text = _build_command_lines(page_cmds)

        prev_btn = discord.ui.Button(
            label="◀ Previous",
            style=discord.ButtonStyle.secondary,
            disabled=page <= 1,
            custom_id="cat_prev",
        )
        back_btn = discord.ui.Button(
            label="↩ Main Menu",
            style=discord.ButtonStyle.secondary,
            custom_id="cat_back",
        )
        next_btn = discord.ui.Button(
            label="Next ▶",
            style=discord.ButtonStyle.secondary,
            disabled=page >= total_pages,
            custom_id="cat_next",
        )

        _cat = category
        _page = page
        _owner = is_owner
        _oname = owner_name
        _oid = owner_id
        _inv = support_invite

        async def _prev(interaction: discord.Interaction):
            await interaction.response.edit_message(
                view=CategoryView(_cat, _page - 1, _owner, _oname, _oid, _inv)
            )

        async def _back(interaction: discord.Interaction):
            await interaction.response.edit_message(
                view=HelpMenuView(_owner, _oname, _oid, _inv)
            )

        async def _next(interaction: discord.Interaction):
            await interaction.response.edit_message(
                view=CategoryView(_cat, _page + 1, _owner, _oname, _oid, _inv)
            )

        prev_btn.callback = _prev
        back_btn.callback = _back
        next_btn.callback = _next

        owner_notice = (
            f"\n-# {E.get('owner', '🔐')} Owner category — restricted commands"
            if is_owner and category == "owner" else ""
        )
        perms_line = f"\n-# {E.get('lock', '🔒')} {perms_note}" if perms_note else ""

        self.add_item(
            discord.ui.Container(
                discord.ui.TextDisplay(f"# {cat_emoji}  {cat_label}"),
                discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
                discord.ui.TextDisplay(f"**Page {page} of {total_pages}**"),
                discord.ui.Separator(),
                discord.ui.TextDisplay(cmd_text),
                discord.ui.Separator(),
                discord.ui.TextDisplay(
                    f"-# {E.get('bot', '🤖')} Powered by Cybork  ·  Use `>help` to return to the main menu"
                    f"{perms_line}{owner_notice}"
                ),
                discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
                discord.ui.ActionRow(prev_btn, back_btn, next_btn),
                accent_colour=WHITE,
            )
        )


class HelpMenuView(discord.ui.LayoutView):
    def __init__(
        self,
        is_owner: bool = False,
        owner_name: str | None = None,
        owner_id: int | None = None,
        support_invite: str | None = None,
    ):
        super().__init__(timeout=300)
        self._is_owner = is_owner
        self._owner_name = owner_name
        self._owner_id = owner_id
        self._support_invite = support_invite

        merged = _merged_data(is_owner)

        options = [
            discord.SelectOption(
                label="All Commands",
                description="View every available command",
                emoji=E.get("note", "📋"),
                value="all",
            ),
        ]
        for key, data in merged.items():
            options.append(
                discord.SelectOption(
                    label=data["label"],
                    description=data["description"],
                    emoji=data["emoji"],
                    value=key,
                )
            )

        module_select = discord.ui.Select(
            placeholder="Browse Cybork Command Categories",
            options=options,
            custom_id="help_module_select",
        )

        _owner = is_owner
        _oname = owner_name
        _oid = owner_id
        _inv = support_invite

        async def _on_select(interaction: discord.Interaction):
            selected = module_select.values[0]
            await interaction.response.edit_message(
                view=CategoryView(selected, is_owner=_owner, owner_name=_oname, owner_id=_oid, support_invite=_inv)
            )

        module_select.callback = _on_select

        invite_btn = discord.ui.Button(
            label="Invite Bot",
            style=discord.ButtonStyle.link,
            url="https://discord.com/oauth2/authorize?scope=applications.commands+bot&permissions=274878024704",
            emoji=E.get("link", "🔗"),
        )

        support_url = support_invite or "https://discord.gg/"
        support_btn = discord.ui.Button(
            label="Support Server",
            style=discord.ButtonStyle.link,
            url=support_url,
            emoji=E.get("support", "📩"),
            disabled=(not support_invite),
        )

        owner_tag = (
            f"\n-# {E.get('owner', '🔐')} Owner mode — restricted category visible"
            if is_owner else ""
        )

        if owner_id and owner_name:
            owner_line = (
                f"\n{E.get('owner', '🔐')} **Developer:** "
                f"[**{owner_name}**](https://discord.com/users/{owner_id})"
            )
        elif owner_id:
            owner_line = (
                f"\n{E.get('owner', '🔐')} **Developer:** "
                f"[**{owner_id}**](https://discord.com/users/{owner_id})"
            )
        else:
            owner_line = ""

        self.add_item(
            discord.ui.Container(
                discord.ui.TextDisplay(f"# {E.get('bot', '🤖')}  Cybork Command Menu"),
                discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
                discord.ui.TextDisplay(
                    f"**Getting Started**\n"
                    f"Use `>scan @member` to generate a risk intelligence report.\n"
                    f"All commands use the `>` prefix  —  e.g. `>ping`, `>help`, `>scan @user`\n\n"
                    f"Select a category below to browse all commands."
                ),
                discord.ui.Separator(),
                discord.ui.TextDisplay(
                    f"**Need Help?**\n"
                    f"Visit our **[Support Server]({support_url})** or use `>about` for more info."
                    f"{owner_line}{owner_tag}"
                ),
                discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
                discord.ui.ActionRow(module_select),
                discord.ui.ActionRow(invite_btn, support_btn),
                accent_colour=WHITE,
            )
        )
