import discord

COMMANDS_DATA = {
    "scan": {
        "label": "Scan & Risk",
        "emoji": "🔍",
        "description": "Risk intelligence commands",
        "commands": [
            ("/scan @member", "Full risk intelligence report with visual card"),
            ("/risk @member", "Quick LOW/MEDIUM/HIGH classification"),
            ("/altsuspect @member", "Alt account detection analysis"),
            ("/behavior @member", "Behavioral pattern analysis"),
            ("/trustscore @member", "Reputation and trust score"),
        ],
    },
    "moderation": {
        "label": "Moderation",
        "emoji": "🛡️",
        "description": "Server moderation commands",
        "commands": [
            ("/warn @member [reason]", "Issue a warning to a member"),
            ("/mute @member <duration> [reason]", "Timeout a member (e.g. 10m, 2h, 1d)"),
            ("/kick @member [reason]", "Kick a member from the server"),
            ("/ban @member [reason]", "Ban a member from the server"),
            ("/lock [channel] [reason]", "Lock a channel for members"),
            ("/unlock [channel] [reason]", "Unlock a channel for members"),
            ("/slowmode <seconds> [channel]", "Set slowmode delay"),
        ],
    },
    "history": {
        "label": "History & Flags",
        "emoji": "📋",
        "description": "Moderation history and flagging",
        "commands": [
            ("/warnings @member", "View all warnings for a member"),
            ("/history @member", "Full moderation action history"),
            ("/notes @member [note]", "View or add private mod notes"),
            ("/flag @member [reason]", "Flag a member as suspicious"),
            ("/unflag @member", "Remove suspicious flag"),
        ],
    },
    "analytics": {
        "label": "Analytics",
        "emoji": "📊",
        "description": "Server analytics and activity",
        "commands": [
            ("/serverstats", "Overall server statistics"),
            ("/topusers", "Most active members"),
            ("/inactive", "Members with no activity"),
            ("/channels", "Channel activity overview"),
            ("/report", "Full server health report"),
            ("/profile @member", "Member profile card"),
            ("/activity @member", "Member activity report"),
        ],
    },
    "config": {
        "label": "Configuration",
        "emoji": "⚙️",
        "description": "Bot and server configuration",
        "commands": [
            ("/setup", "View current server configuration"),
            ("/setmodlog #channel", "Set moderation log channel"),
            ("/setalerts #channel", "Set alerts channel"),
            ("/antispam <on/off>", "Toggle anti-spam filter"),
            ("/antilink <on/off>", "Toggle anti-link filter"),
            ("/capsfilter <on/off>", "Toggle caps filter"),
            ("/alerts risk <on/off>", "Toggle risk join alerts"),
            ("/autorole set @role", "Set auto-role on join"),
            ("/autokick set <days>", "Set inactive member auto-kick"),
        ],
    },
    "utility": {
        "label": "Utility",
        "emoji": "🔧",
        "description": "General utility commands",
        "commands": [
            ("/ping", "Check bot latency"),
            ("/about", "About Cybork"),
            ("/help", "This command menu"),
            (">ping", "Text prefix ping"),
            (">help", "Text prefix help"),
            (">about", "Text prefix about"),
        ],
    },
}

ALL_COMMANDS = [
    (cmd, desc)
    for cat in COMMANDS_DATA.values()
    for cmd, desc in cat["commands"]
]

PER_PAGE = 6
ACCENT = discord.Color.from_rgb(124, 58, 237)
ACCENT_UTIL = discord.Color.from_rgb(59, 130, 246)


def _build_command_lines(cmds: list[tuple]) -> str:
    return "\n".join(f"• `{cmd}` — {desc}" for cmd, desc in cmds) or "*No commands found.*"


class CategoryView(discord.ui.LayoutView):
    def __init__(self, category: str = "all", page: int = 1):
        super().__init__(timeout=300)
        self.category = category
        self.page = page

        if category == "all":
            cat_label, cat_emoji = "All Commands", "📋"
            cmds = ALL_COMMANDS
        else:
            data = COMMANDS_DATA[category]
            cat_label = data["label"]
            cat_emoji = data["emoji"]
            cmds = data["commands"]

        total_pages = max(1, (len(cmds) + PER_PAGE - 1) // PER_PAGE)
        page_cmds = cmds[(page - 1) * PER_PAGE: page * PER_PAGE]
        cmd_text = _build_command_lines(page_cmds)

        prev_btn = discord.ui.Button(
            label="◀ Previous",
            style=discord.ButtonStyle.primary,
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
            style=discord.ButtonStyle.primary,
            disabled=page >= total_pages,
            custom_id="cat_next",
        )

        _cat = category
        _page = page

        async def _prev(interaction: discord.Interaction):
            await interaction.response.edit_message(view=CategoryView(_cat, _page - 1))

        async def _back(interaction: discord.Interaction):
            await interaction.response.edit_message(view=HelpMenuView())

        async def _next(interaction: discord.Interaction):
            await interaction.response.edit_message(view=CategoryView(_cat, _page + 1))

        prev_btn.callback = _prev
        back_btn.callback = _back
        next_btn.callback = _next

        self.add_item(
            discord.ui.Container(
                discord.ui.TextDisplay(f"# {cat_emoji}  {cat_label}"),
                discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
                discord.ui.TextDisplay(f"**Page {page} of {total_pages}**"),
                discord.ui.Separator(),
                discord.ui.TextDisplay(cmd_text),
                discord.ui.Separator(),
                discord.ui.TextDisplay("-# Powered by Cybork  ·  Use `/help` to return to the main menu"),
                discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
                discord.ui.ActionRow(prev_btn, back_btn, next_btn),
                accent_colour=ACCENT_UTIL,
            )
        )


class HelpMenuView(discord.ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=300)

        options = [
            discord.SelectOption(
                label="All Commands",
                description="View every available command",
                emoji="📋",
                value="all",
            ),
        ]
        for key, data in COMMANDS_DATA.items():
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

        async def _on_select(interaction: discord.Interaction):
            selected = module_select.values[0]
            await interaction.response.edit_message(view=CategoryView(selected))

        module_select.callback = _on_select

        invite_btn = discord.ui.Button(
            label="Invite Bot",
            style=discord.ButtonStyle.link,
            url="https://discord.com/oauth2/authorize?scope=applications.commands+bot&permissions=274878024704",
            emoji="🔗",
        )
        support_btn = discord.ui.Button(
            label="Support Server",
            style=discord.ButtonStyle.link,
            url="https://discord.gg/",
            emoji="📩",
        )

        self.add_item(
            discord.ui.Container(
                discord.ui.TextDisplay("# 🤖  Cybork Command Menu"),
                discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
                discord.ui.TextDisplay(
                    "**Getting Started**\n"
                    "Use `/scan @member` to generate a risk intelligence report.\n"
                    "Prefix commands are also available with `>`  —  e.g. `>ping`, `>help`\n\n"
                    "Select a category below to browse all commands."
                ),
                discord.ui.Separator(),
                discord.ui.TextDisplay(
                    "**Need Help?**\n"
                    "Visit our **[Support Server](https://discord.gg/)** or use `/about` for more info."
                ),
                discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
                discord.ui.ActionRow(module_select),
                discord.ui.ActionRow(invite_btn, support_btn),
                accent_colour=ACCENT,
            )
        )
