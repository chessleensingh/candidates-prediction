"""
Configuration loader. Reads from environment variables (set via .env or system).
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the project root (same directory as this file)
load_dotenv(Path(__file__).parent / ".env")


def _require(key: str) -> str:
    val = os.getenv(key)
    if not val:
        raise EnvironmentError(
            f"Required environment variable '{key}' is not set. "
            f"Copy .env.example to .env and fill in the values."
        )
    return val


# Discord bot token
BOT_TOKEN: str = _require("DISCORD_BOT_TOKEN")

# Guild (server) ID where the bot operates.
# Leave empty to register commands globally (takes up to 1 hour to propagate).
GUILD_ID: int | None = int(os.getenv("DISCORD_GUILD_ID", "0")) or None

# Discord role ID that grants admin privileges for entering results
ADMIN_ROLE_ID: int | None = int(os.getenv("ADMIN_ROLE_ID", "0")) or None

# Channel IDs (optional) — if set, certain commands are restricted to these channels
PREDICTIONS_CHANNEL_ID: int | None = (
    int(os.getenv("PREDICTIONS_CHANNEL_ID", "0")) or None
)
RESULTS_CHANNEL_ID: int | None = (
    int(os.getenv("RESULTS_CHANNEL_ID", "0")) or None
)
ANNOUNCEMENTS_CHANNEL_ID: int | None = (
    int(os.getenv("ANNOUNCEMENTS_CHANNEL_ID", "0")) or None
)

# How many seconds between the background task tick (auto-score check)
BACKGROUND_TASK_INTERVAL: int = int(os.getenv("BACKGROUND_TASK_INTERVAL", "120"))
