import discord

COMMANDS_DATA = {
    "scan": {
        "label": "Scan & Analysis",
        "emoji": "🔍",
        "description": "Member risk intelligence commands",
        "commands": [
            ("/scan @member", "Generate a full risk intelligence report for a member"),
        ],
    },
    "utility": {
        "label": "Utility",
        "emoji": "⚙️",
        "description": "General utility and information commands",
        "commands": [
            ("/ping", "Check the bot's response latency"),
            ("/about", "Learn about NotHide and its features"),
            ("/help", "View the interactive command menu"),
        ],
    },
}

ALL_COMMANDS = [
    (cmd, desc)
    for cat in COMMANDS_DATA.values()
    for cmd, desc in cat["commands"]
]

PER_PAGE = 7
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
        page_cmds = cmds[(page - 1) * PER_PAGE : page * PER_PAGE]
        cmd_text = _build_command_lines(page_cmds)

        prev_btn = discord.ui.Button(
            label="Previous",
            style=discord.ButtonStyle.primary,
            disabled=page <= 1,
            custom_id="cat_prev",
        )
        back_btn = discord.ui.Button(
            label="Back",
            style=discord.ButtonStyle.secondary,
            custom_id="cat_back",
        )
        next_btn = discord.ui.Button(
            label="Next",
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
                discord.ui.TextDisplay(f"**(Page {page}/{total_pages})**"),
                discord.ui.Separator(),
                discord.ui.TextDisplay(cmd_text),
                discord.ui.Separator(),
                discord.ui.TextDisplay(
                    "Use `/help` to return to the main menu"
                ),
                discord.ui.TextDisplay("-# Powered by NotHide"),
                discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
                prev_btn,
                back_btn,
                next_btn,
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
            placeholder="NotHide Command Modules",
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
                discord.ui.TextDisplay("# NotHide Command Menu"),
                discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
                discord.ui.TextDisplay(
                    "**Command Information**\n"
                    "Select a category from the menu below to view available commands.\n\n"
                    "Use `/scan @member` to generate a risk intelligence report."
                ),
                discord.ui.Separator(),
                discord.ui.TextDisplay(
                    "**Found a Bug?**\n"
                    "Report issues using `/about` to help us improve the bot."
                ),
                discord.ui.TextDisplay(
                    "**Need Extra Help?**\n"
                    "Visit our **[Support Server](https://discord.gg/)** for assistance."
                ),
                discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
                discord.ui.TextDisplay("Developer: **NotHide**"),
                discord.ui.Separator(),
                module_select,
                invite_btn,
                support_btn,
                accent_colour=ACCENT,
            )
        )
