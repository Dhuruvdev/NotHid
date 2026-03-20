# NotHide — Discord Risk Intelligence Bot

## Overview
NotHide is a premium Discord bot that analyzes server members and generates risk intelligence reports using multi-factor scoring. It uses discord.py 2.x (slash commands + interactions) and Pillow for generating analysis card images.

## Architecture

### Files
- **main.py** — Bot entry point. Defines the bot class, `/scan`, `/ping`, `/about` slash commands, and the `on_member_join` event.
- **scoring.py** — Risk algorithm. Produces a 0–100 score from four signal categories: account age, username patterns, join cluster detection, and behavioral similarity.
- **image_generator.py** — Pillow image generation. Produces a 920×510px dark-theme analysis card PNG with gradient accents, circular avatar, risk bar, and signal indicators.
- **views.py** — Discord UI components. `AnalysisView` with three buttons: View Details, Why this score?, Enable Auto Detection ⚡.
- **storage.py** — JSON-based storage at `data/user_history.json`. Tracks join history (last 500) and scan results per guild.

### Assets
- `assets/fonts/` — Font directory (currently uses system DejaVu fonts at `/usr/share/fonts/truetype/dejavu/`)

## Configuration

### Environment Variables
- `DISCORD_TOKEN` (required) — Discord bot token
- `GUILD_ID` (optional) — If set, syncs slash commands instantly to this guild. Otherwise global sync (up to 1 hour).

### Discord Developer Portal Requirements
- **Privileged Intents**: `Server Members Intent` must be enabled for `on_member_join` to receive events.
- **Bot Permissions**: Read Messages, Send Messages, Attach Files, Use Slash Commands.

## Scoring Algorithm

| Signal | Max Points | Notes |
|---|---|---|
| Account age | 32 | < 3 days = 32pts, scales down |
| Username pattern | 25 | Regex patterns, digit ratio, randomness |
| Behavioral similarity | 25 | SequenceMatcher against last 50 joins |
| Join cluster | 26 | Join timing within 10min/1hr windows |

**Classifications:** LOW (0–39), MEDIUM (40–69), HIGH (70–100)

## Image Card Design
- **Size:** 920 × 510 px PNG
- **Theme:** Dark (#0B0B0F) with purple/blue gradient glow accents
- **Fonts:** DejaVu Sans (system fonts)
- **Risk colors:** Green (LOW), Yellow (MEDIUM), Red (HIGH)
- **Sections:** Header → User info + avatar → Score + risk bar → Key signals → Footer

## Workflow
- **Name:** `NotHide Bot`
- **Command:** `python main.py`
- **Type:** Console (background service)

## Dependencies
- `discord.py` 2.7.1
- `Pillow` 12.1.1
- `aiohttp` 3.13.3
