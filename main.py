import os
import sys
import logging
import discord
from discord.ext import commands
from datetime import datetime, timezone

ANSI = {
    "reset":   "\033[0m",
    "bold":    "\033[1m",
    "grey":    "\033[38;5;245m",
    "white":   "\033[97m",
    "cyan":    "\033[96m",
    "green":   "\033[92m",
    "yellow":  "\033[93m",
    "red":     "\033[91m",
    "magenta": "\033[95m",
    "blue":    "\033[94m",
    "bg_dark": "\033[48;5;235m",
}

LEVEL_STYLES = {
    "DEBUG":    (ANSI["grey"],    "DBG"),
    "INFO":     (ANSI["cyan"],    "INF"),
    "WARNING":  (ANSI["yellow"],  "WRN"),
    "ERROR":    (ANSI["red"],     "ERR"),
    "CRITICAL": (ANSI["magenta"], "CRT"),
}

LOGGER_COLORS = {
    "cybork":          ANSI["green"],
    "cybork.boot":     ANSI["blue"],
    "cybork.cogs":     ANSI["cyan"],
    "discord":          ANSI["grey"],
    "discord.gateway":  ANSI["grey"],
    "discord.client":   ANSI["grey"],
    "discord.http":     ANSI["grey"],
}


class CyborkFormatter(logging.Formatter):
    WIDTH = 80

    def format(self, record: logging.LogRecord) -> str:
        color, tag = LEVEL_STYLES.get(record.levelname, (ANSI["white"], record.levelname[:3].upper()))
        ts = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")

        name = record.name
        name_color = ANSI["white"]
        for key, clr in LOGGER_COLORS.items():
            if name.startswith(key):
                name_color = clr
                break

        name_short = name.split(".")[-1][:16]

        prefix = (
            f"{ANSI['grey']}{ts}{ANSI['reset']} "
            f"{color}{ANSI['bold']}[{tag}]{ANSI['reset']} "
            f"{name_color}{name_short:<16}{ANSI['reset']} "
            f"{ANSI['grey']}│{ANSI['reset']} "
        )

        message = record.getMessage()
        if record.exc_info:
            message += "\n" + self.formatException(record.exc_info)

        return prefix + message


def _setup_logging():
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(CyborkFormatter())

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()
    root.addHandler(handler)

    logging.getLogger("discord").setLevel(logging.WARNING)
    logging.getLogger("discord.http").setLevel(logging.WARNING)
    logging.getLogger("discord.gateway").setLevel(logging.WARNING)


_setup_logging()

log = logging.getLogger("cybork")
boot_log = logging.getLogger("cybork.boot")
cog_log = logging.getLogger("cybork.cogs")

TOKEN = os.environ.get("DISCORD_TOKEN")
if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN environment variable is not set.")

_guild_id_raw = os.environ.get("GUILD_ID", "").strip()
GUILD_ID = _guild_id_raw if _guild_id_raw.isdigit() else None

EXTENSIONS = [
    "cogs.utility",
    "cogs.user",
    "cogs.risk",
    "cogs.moderation",
    "cogs.history",
    "cogs.config",
    "cogs.automation",
    "cogs.analytics",
    "cogs.alerts",
    "cogs.owner",
]

intents = discord.Intents.default()
intents.members = True
intents.message_content = True


class CyborkBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=commands.when_mentioned,
            intents=intents,
            help_command=None,
        )
        self.start_time = datetime.now(timezone.utc)

    async def setup_hook(self):
        sep = f"{ANSI['grey']}{'─' * 60}{ANSI['reset']}"
        print(sep)
        boot_log.info(f"Loading {len(EXTENSIONS)} cog extensions...")

        failed = []
        for ext in EXTENSIONS:
            try:
                await self.load_extension(ext)
                cog_log.info(f"Loaded  ✓  {ext}")
            except Exception as e:
                cog_log.error(f"Failed  ✗  {ext}  →  {e}")
                failed.append(ext)

        all_cmds = list(self.tree.walk_commands())
        boot_log.info(f"Commands registered: {len(all_cmds)}")

        if GUILD_ID:
            guild_obj = discord.Object(id=int(GUILD_ID))
            self.tree.copy_global_to(guild=guild_obj)
            await self.tree.sync(guild=guild_obj)
            boot_log.info(f"Synced to guild {GUILD_ID} (instant)")
        else:
            await self.tree.sync()
            boot_log.info("Synced globally (up to 1h propagation)")

        if failed:
            boot_log.warning(f"{len(failed)} extension(s) failed to load: {', '.join(failed)}")

        print(sep)

    async def on_ready(self):
        sep = f"{ANSI['green']}{'━' * 60}{ANSI['reset']}"
        print(sep)
        log.info(f"Cybork is online   →   {self.user}  ({self.user.id})")
        log.info(f"Guilds: {len(self.guilds)}   •   Latency: {round(self.latency * 1000)}ms")
        print(sep)
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="for suspicious patterns",
            )
        )

    async def on_member_join(self, member: discord.Member):
        import storage
        storage.record_join(member.id, member.name, member.guild.id, member.created_at)
        log.info(f"Join recorded  →  {member.name} ({member.id})  in  {member.guild.name}")

    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        import storage
        if message.guild:
            storage.record_message(message.author.id, message.guild.id, message.channel.id)
        await self.process_commands(message)

    async def on_app_command_completion(self, interaction: discord.Interaction, command):
        guild_name = interaction.guild.name if interaction.guild else "DM"
        log.info(f"/{command.name}  ←  {interaction.user}  in  [{guild_name}]")

    async def on_command_error(self, ctx, error):
        log.error(f"Command error: {error}")

    async def on_error(self, event_method: str, *args, **kwargs):
        log.error(f"Unhandled error in event: {event_method}", exc_info=True)


bot = CyborkBot()

if __name__ == "__main__":
    print(f"\n{ANSI['bold']}{ANSI['green']}  Cybork Bot  —  Starting up...{ANSI['reset']}\n")
    bot.run(TOKEN, log_handler=None)
