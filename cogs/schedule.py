"""
Schedule cog — tournament schedule, round info, and prediction-close times.

Slash commands:
  /schedule open [round]    — show the full Open schedule or a specific round
  /schedule women [round]   — same for Women's section
  /nextround                — show when the next round starts for both sections
  /players open             — list Open section players
  /players women            — list Women's section players
  /about                    — general info about the tournament
"""

import logging
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands

import database
from tournament_data import (
    OPEN_PLAYERS,
    WOMEN_PLAYERS,
    OPEN_ROUND_DATES,
    WOMEN_ROUND_DATES,
    SECTION_OPEN,
    SECTION_WOMEN,
    PREDICTION_CUTOFF_MINUTES,
)

log = logging.getLogger(__name__)

ROUND_DATES = {
    SECTION_OPEN: OPEN_ROUND_DATES,
    SECTION_WOMEN: WOMEN_ROUND_DATES,
}

REST_DAYS = ["April 2", "April 6", "April 10", "April 13"]


class Schedule(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    # ------------------------------------------------------------------
    # /schedule
    # ------------------------------------------------------------------

    schedule_group = app_commands.Group(
        name="schedule",
        description="Show the tournament schedule.",
    )

    @schedule_group.command(
        name="open", description="Show the Open section schedule."
    )
    @app_commands.describe(round="Specific round (1-14). Leave blank to show full schedule.")
    async def schedule_open(
        self, interaction: discord.Interaction, round: int | None = None
    ) -> None:
        await self._show_schedule(interaction, SECTION_OPEN, round)

    @schedule_group.command(
        name="women", description="Show the Women's section schedule."
    )
    @app_commands.describe(round="Specific round (1-14). Leave blank to show full schedule.")
    async def schedule_women(
        self, interaction: discord.Interaction, round: int | None = None
    ) -> None:
        await self._show_schedule(interaction, SECTION_WOMEN, round)

    async def _show_schedule(
        self,
        interaction: discord.Interaction,
        section: str,
        round_number: int | None,
    ) -> None:
        section_label = "Open" if section == SECTION_OPEN else "Women's"

        if round_number is not None:
            # Single round view — show pairings + prediction cutoff
            games = database.get_games_for_round(section, round_number)
            if not games:
                await interaction.response.send_message(
                    f"No games found for {section_label} Round {round_number}.",
                    ephemeral=True,
                )
                return

            round_dt = ROUND_DATES[section][round_number - 1]
            from datetime import timedelta
            cutoff_dt = round_dt - timedelta(minutes=PREDICTION_CUTOFF_MINUTES)

            embed = discord.Embed(
                title=f"2026 Candidates — {section_label} Round {round_number}",
                color=discord.Color.gold(),
            )
            embed.add_field(
                name="Round Start",
                value=f"<t:{int(round_dt.timestamp())}:F> (<t:{int(round_dt.timestamp())}:R>)",
                inline=False,
            )
            embed.add_field(
                name="Predictions Close",
                value=f"<t:{int(cutoff_dt.timestamp())}:F> (<t:{int(cutoff_dt.timestamp())}:R>)",
                inline=False,
            )
            lines = []
            for g in games:
                result_str = f" → **{g['result']}**" if g["result"] else ""
                lines.append(
                    f"[#{g['game_id']}] **{g['white_player']}** vs **{g['black_player']}**{result_str}"
                )
            embed.add_field(
                name="Games",
                value="\n".join(lines),
                inline=False,
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Full schedule — paginated embeds (3 rounds per embed to stay under limits)
        now = datetime.now(timezone.utc)
        embeds = []
        embed = discord.Embed(
            title=f"2026 Candidates — {section_label} Schedule",
            description=(
                "Toronto, Canada\n"
                f"Rest days: {', '.join(REST_DAYS)}"
            ),
            color=discord.Color.gold(),
        )
        field_count = 0

        dates = ROUND_DATES[section]
        for rnd_idx, round_dt in enumerate(dates, start=1):
            status = ""
            if round_dt < now:
                status = " *(completed)*"
            elif rnd_idx == database.get_current_round(section):
                status = " *(current)*"
            else:
                status = f" (<t:{int(round_dt.timestamp())}:R>)"

            if field_count >= 6:
                embeds.append(embed)
                embed = discord.Embed(color=discord.Color.gold())
                field_count = 0

            embed.add_field(
                name=f"Round {rnd_idx}{status}",
                value=f"<t:{int(round_dt.timestamp())}:D> at <t:{int(round_dt.timestamp())}:t> UTC",
                inline=True,
            )
            field_count += 1

        embeds.append(embed)
        await interaction.response.send_message(embeds=embeds[:5], ephemeral=True)

    # ------------------------------------------------------------------
    # /nextround
    # ------------------------------------------------------------------

    @app_commands.command(
        name="nextround",
        description="Show when the next round starts and when predictions close.",
    )
    async def nextround(self, interaction: discord.Interaction) -> None:
        embed = discord.Embed(
            title="Next Rounds",
            color=discord.Color.blue(),
        )
        for section in (SECTION_OPEN, SECTION_WOMEN):
            info = database.get_next_round_info(section)
            section_label = "Open" if section == SECTION_OPEN else "Women's"
            if info is None:
                embed.add_field(
                    name=section_label, value="Tournament complete.", inline=False
                )
                continue
            round_ts = int(
                datetime.fromisoformat(info["round_start_utc"]).timestamp()
            )
            cutoff_ts = int(
                datetime.fromisoformat(info["cutoff_utc"]).timestamp()
            )
            embed.add_field(
                name=f"{section_label} — Round {info['round_number']}",
                value=(
                    f"Starts: <t:{round_ts}:F> (<t:{round_ts}:R>)\n"
                    f"Predictions close: <t:{cutoff_ts}:F> (<t:{cutoff_ts}:R>)"
                ),
                inline=False,
            )
        await interaction.response.send_message(embed=embed)

    # ------------------------------------------------------------------
    # /players
    # ------------------------------------------------------------------

    players_group = app_commands.Group(
        name="players",
        description="List the players in each section.",
    )

    @players_group.command(name="open", description="List Open section players.")
    async def players_open(self, interaction: discord.Interaction) -> None:
        await self._show_players(interaction, SECTION_OPEN)

    @players_group.command(name="women", description="List Women's section players.")
    async def players_women(self, interaction: discord.Interaction) -> None:
        await self._show_players(interaction, SECTION_WOMEN)

    async def _show_players(
        self, interaction: discord.Interaction, section: str
    ) -> None:
        players = OPEN_PLAYERS if section == SECTION_OPEN else WOMEN_PLAYERS
        section_label = "Open" if section == SECTION_OPEN else "Women's"
        embed = discord.Embed(
            title=f"2026 Candidates — {section_label} Players",
            color=discord.Color.dark_gold(),
        )
        numbered = "\n".join(f"{i}. {p}" for i, p in enumerate(players, 1))
        embed.description = numbered
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ------------------------------------------------------------------
    # /about
    # ------------------------------------------------------------------

    @app_commands.command(
        name="about",
        description="General information about the 2026 Candidates Tournament.",
    )
    async def about(self, interaction: discord.Interaction) -> None:
        embed = discord.Embed(
            title="2026 FIDE Candidates Tournament",
            description=(
                "The 2026 Candidates Tournament determines the challenger to the reigning "
                "World Chess Champion.\n\n"
                "**Location:** Pegeia, Cyprus (Cap St Georges Hotel and Resort)\n"
                "**Format:** Double round-robin (each player faces every other player twice)\n"
                "**Dates:** March 29 – April 15, 2026\n"
                "**14 rounds** | 8 players per section\n"
                "**Rest days:** April 2, 6, 10, 13\n"
                "**Round start:** 15:30 EEST / 12:30 UTC"
            ),
            color=discord.Color.dark_gold(),
        )
        embed.add_field(
            name="Scoring (Predictions)",
            value=(
                "Correct prediction: **+3 points**\n"
                "Correct decisive result bonus: **+1 point**\n"
                "(bonus applies when you correctly call a win, not a draw)"
            ),
            inline=False,
        )
        embed.add_field(
            name="How to Predict",
            value=(
                "`/predict open` or `/predict women` to predict a round.\n"
                "Predictions close **30 minutes** before each round starts.\n"
                "You can update your prediction any time before the window closes."
            ),
            inline=False,
        )
        embed.set_footer(text="Times shown in your local timezone via Discord timestamps.")
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Schedule(bot))
