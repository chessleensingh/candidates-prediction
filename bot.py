"""
Entry point for the 2026 Chess Candidates Prediction bot.

Usage:
    python bot.py
"""

import asyncio
import logging
import random
import sys
from pathlib import Path

import discord
from discord.ext import commands, tasks

import config
import database

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(Path(__file__).parent / "bot.log", encoding="utf-8"),
    ],
)
log = logging.getLogger("bot")

# ---------------------------------------------------------------------------
# Bot setup
# ---------------------------------------------------------------------------

STATUSES = [
    "Watching Nepomniachtchi blunder",
    "Watching Gukesh forget his prep",
    "Playing Magnus Carlsen (he declined)",
    "Listening to Fabiano think for 45 min",
    "Watching for the next Bongcloud",
    "Trying to replace Octopus Paul",
    "Watching Hikaru speedrun the standings",
    "Playing e4 (objectively best)",
    "Watching a draw offer get declined",
    "Listening to piece sacrifices",
    "Watching someone blunder a won endgame",
    "Playing 1. d4 (the superior choice)",
    "Watching prep go out the window on move 8",
    "Competing: World's Worst Chess Oracle",
    "Watching GMs stare at each other for 6 hours",
]

COGS = [
    "cogs.predictions",
    "cogs.results",
    "cogs.schedule",
    "cogs.leaderboard",
]

intents = discord.Intents.default()
intents.message_content = False  # Not needed for slash commands


class CandidatesBot(commands.Bot):
    def __init__(self) -> None:
        super().__init__(
            command_prefix="!",  # fallback prefix, not used for slash commands
            intents=intents,
            help_command=None,
        )
        self.guild_id = config.GUILD_ID

    async def setup_hook(self) -> None:
        log.info("Initialising database...")
        database.init_db()

        log.info("Loading cogs...")
        for cog in COGS:
            try:
                await self.load_extension(cog)
                log.info("  Loaded: %s", cog)
            except Exception as exc:
                log.error("  Failed to load %s: %s", cog, exc, exc_info=True)

        # Sync slash commands
        if self.guild_id:
            guild = discord.Object(id=self.guild_id)
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
            log.info("Synced %d guild command(s) to guild %s.", len(synced), self.guild_id)
        else:
            synced = await self.tree.sync()
            log.info("Synced %d global command(s).", len(synced))

    async def on_ready(self) -> None:
        log.info("Logged in as %s (ID: %s)", self.user, self.user.id)
        self.rotate_status.start()

    @tasks.loop(seconds=10)
    async def rotate_status(self) -> None:
        status = random.choice(STATUSES)
        await self.change_presence(
            activity=discord.CustomActivity(name=status)
        )

    async def on_command_error(
        self, ctx: commands.Context, error: commands.CommandError
    ) -> None:
        log.error("Command error: %s", error)


async def main() -> None:
    bot = CandidatesBot()
    async with bot:
        await bot.start(config.BOT_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
