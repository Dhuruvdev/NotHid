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
        "commands": [
            (">warn @member [reason]",          "Issue a warning to a member"),
            (">mute @member <duration> [reason]","Timeout a member (e.g. 10m, 2h, 1d)"),
            (">kick @member [reason]",           "Kick a member from the server"),
            (">ban @member [reason]",            "Ban a member from the server"),
            (">lock [#channel] [reason]",        "Lock a channel for members"),
            (">unlock [#channel] [reason]",      "Unlock a channel for members"),
            (">slowmode <seconds> [#channel]",   "Set slowmode delay"),
        ],
    },
    "history": {
        "label": "History & Flags",
        "emoji": E.get("note", "📋"),
        "description": "Moderation history and flagging",
        "commands": [
            (">warnings @member",      "View all warnings for a member"),
            (">history @member",       "Full moderation action history"),
            (">notes @member [note]",  "View or add private mod notes"),
            (">flag @member [reason]", "Flag a member as suspicious"),
            (">unflag @member",        "Remove suspicious flag"),
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
            (">report",            "Full server health report"),
            (">profile @member",   "Member profile card"),
            (">activity @member",  "Member activity report"),
        ],
    },
    "config": {
        "label": "Configuration",
        "emoji": E.get("gear", "⚙️"),
        "description": "Bot and server configuration",
        "commands": [
            (">setup",                "View current server configuration"),
            (">setmodlog #channel",   "Set moderation log channel"),
            (">setalerts #channel",   "Set alerts channel"),
            (">antispam <on/off>",    "Toggle anti-spam filter"),
            (">antilink <on/off>",    "Toggle anti-link filter"),
            (">capsfilter <on/off>",  "Toggle caps filter"),
            (">alertsrisk <on/off>",  "Toggle risk join alerts"),
            (">autoroleset @role",    "Set auto-role on join"),
            (">autokickset <days>",   "Set inactive member auto-kick threshold"),
        ],
    },
    "utility": {
        "label": "Utility",
        "emoji": E.get("bot", "🤖"),
        "description": "General utility commands",
        "commands": [
            (">ping",                    "Check bot latency"),
            (">about",                   "About Cybork"),
            (">help",                    "This command menu"),
            (">botinfo",                 "Detailed bot information"),
            (">alertsstatus",            "View alert configuration"),
            (">autorolestatus",          "View auto-role configuration"),
            (">autowarnspam <on/off>",   "Toggle auto-warn for spam"),
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
        ],
    },
}

ALL_COMMANDS = [
    (cmd, desc)
    for cat in COMMANDS_DATA.values()
    for cmd, desc in cat["commands"]
]

PER_PAGE = 6


def _build_command_lines(cmds: list[tuple]) -> str:
    return "\n".join(f"• `{cmd}` — {desc}" for cmd, desc in cmds) or "*No commands found.*"


def _merged_data(is_owner: bool) -> dict:
    if is_owner:
        return {**COMMANDS_DATA, **OWNER_COMMANDS_DATA}
    return COMMANDS_DATA


class CategoryView(discord.ui.LayoutView):
    def __init__(self, category: str = "all", page: int = 1, is_owner: bool = False):
        super().__init__(timeout=300)
        self.category = category
        self.page = page
        self._is_owner = is_owner

        merged = _merged_data(is_owner)

        if category == "all":
            cat_label = "All Commands"
            cat_emoji = E.get("note", "📋")
            cmds = [
                (cmd, desc)
                for cat in merged.values()
                for cmd, desc in cat["commands"]
            ]
        else:
            data = merged[category]
            cat_label = data["label"]
            cat_emoji = data["emoji"]
            cmds = data["commands"]

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

        async def _prev(interaction: discord.Interaction):
            await interaction.response.edit_message(view=CategoryView(_cat, _page - 1, _owner))

        async def _back(interaction: discord.Interaction):
            await interaction.response.edit_message(view=HelpMenuView(_owner))

        async def _next(interaction: discord.Interaction):
            await interaction.response.edit_message(view=CategoryView(_cat, _page + 1, _owner))

        prev_btn.callback = _prev
        back_btn.callback = _back
        next_btn.callback = _next

        owner_notice = "\n-# 🔐 Owner category visible — restricted commands" if is_owner and category == "owner" else ""

        self.add_item(
            discord.ui.Container(
                discord.ui.TextDisplay(f"# {cat_emoji}  {cat_label}"),
                discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
                discord.ui.TextDisplay(f"**Page {page} of {total_pages}**"),
                discord.ui.Separator(),
                discord.ui.TextDisplay(cmd_text),
                discord.ui.Separator(),
                discord.ui.TextDisplay(
                    f"-# {E.get('bot', '🤖')} Powered by Cybork  ·  Use `>help` to return to the main menu{owner_notice}"
                ),
                discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
                discord.ui.ActionRow(prev_btn, back_btn, next_btn),
                accent_colour=WHITE,
            )
        )


class HelpMenuView(discord.ui.LayoutView):
    def __init__(self, is_owner: bool = False):
        super().__init__(timeout=300)
        self._is_owner = is_owner

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

        async def _on_select(interaction: discord.Interaction):
            selected = module_select.values[0]
            await interaction.response.edit_message(view=CategoryView(selected, is_owner=_owner))

        module_select.callback = _on_select

        invite_btn = discord.ui.Button(
            label="Invite Bot",
            style=discord.ButtonStyle.link,
            url="https://discord.com/oauth2/authorize?scope=applications.commands+bot&permissions=274878024704",
            emoji=E.get("link", "🔗"),
        )
        support_btn = discord.ui.Button(
            label="Support Server",
            style=discord.ButtonStyle.link,
            url="https://discord.gg/",
            emoji=E.get("support", "📩"),
        )

        owner_tag = f"\n-# {E.get('owner', '🔐')} Owner mode — restricted category visible" if is_owner else ""

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
                    f"Visit our **[Support Server](https://discord.gg/)** or use `>about` for more info.{owner_tag}"
                ),
                discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
                discord.ui.ActionRow(module_select),
                discord.ui.ActionRow(invite_btn, support_btn),
                accent_colour=WHITE,
            )
        )
