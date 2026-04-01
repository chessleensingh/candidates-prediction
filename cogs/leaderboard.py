"""
Leaderboard cog — scores, rankings, and per-user stats.

Slash commands:
  /leaderboard [section]       — overall leaderboard (optionally by section)
  /roundleaderboard open <n>   — who scored best in a specific round
  /roundleaderboard women <n>
  /mystats [section]           — caller's personal stats
  /userstats <user> [section]  — another user's stats
"""

import logging
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands

import database
from tournament_data import (
    SECTION_OPEN,
    SECTION_WOMEN,
    RESULT_WHITE_WIN,
    RESULT_DRAW,
    RESULT_BLACK_WIN,
    RESULT_LABELS,
    POINTS_CORRECT,
    POINTS_DECISIVE_BONUS,
)

log = logging.getLogger(__name__)

RESULT_EMOJI = {
    RESULT_WHITE_WIN: "⬜",
    RESULT_DRAW:      "🟡",
    RESULT_BLACK_WIN: "⬛",
}

MEDALS = ["🥇", "🥈", "🥉"]


class Leaderboard(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    # ------------------------------------------------------------------
    # /leaderboard
    # ------------------------------------------------------------------

    @app_commands.command(
        name="leaderboard",
        description="Show the overall prediction leaderboard.",
    )
    @app_commands.describe(section="Filter by 'open' or 'women'. Leave blank for combined.")
    async def leaderboard(
        self,
        interaction: discord.Interaction,
        section: str | None = None,
    ) -> None:
        section_filter = None
        if section:
            section_filter = section.lower()
            if section_filter not in (SECTION_OPEN, SECTION_WOMEN):
                await interaction.response.send_message(
                    "Section must be 'open' or 'women'.", ephemeral=True
                )
                return

        rows = database.get_leaderboard(section_filter)
        section_label = (
            "Open" if section_filter == SECTION_OPEN
            else "Women's" if section_filter == SECTION_WOMEN
            else "Combined"
        )

        if not rows:
            await interaction.response.send_message(
                "No scores recorded yet. Predictions need to be scored first.",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title=f"Leaderboard — {section_label}",
            description=f"Max per game: {POINTS_CORRECT + POINTS_DECISIVE_BONUS} pts (decisive) | {POINTS_CORRECT} pts (draw)",
            color=discord.Color.gold(),
            timestamp=datetime.now(timezone.utc),
        )

        lines = []
        for i, row in enumerate(rows, start=1):
            medal = MEDALS[i - 1] if i <= 3 else f"**{i}.**"
            accuracy = (
                f"{row['correct'] / row['games_scored'] * 100:.0f}%"
                if row["games_scored"] > 0
                else "—"
            )
            lines.append(
                f"{medal} **{row['username']}** — "
                f"{row['total_points']} pts | "
                f"{row['correct']}/{row['games_scored']} correct ({accuracy})"
            )

        # Chunk into embed fields of 10 lines each to respect Discord limits
        chunk_size = 10
        for start in range(0, len(lines), chunk_size):
            chunk = lines[start : start + chunk_size]
            embed.add_field(
                name=f"Ranks {start + 1}–{start + len(chunk)}",
                value="\n".join(chunk),
                inline=False,
            )

        await interaction.response.send_message(embed=embed)

    # ------------------------------------------------------------------
    # /roundleaderboard
    # ------------------------------------------------------------------

    roundlb_group = app_commands.Group(
        name="roundleaderboard",
        description="Show the leaderboard for a specific round.",
    )

    @roundlb_group.command(
        name="open",
        description="Show the leaderboard for an Open section round.",
    )
    @app_commands.describe(round="Round number (1-14).")
    async def roundlb_open(
        self, interaction: discord.Interaction, round: int
    ) -> None:
        await self._show_round_lb(interaction, SECTION_OPEN, round)

    @roundlb_group.command(
        name="women",
        description="Show the leaderboard for a Women's section round.",
    )
    @app_commands.describe(round="Round number (1-14).")
    async def roundlb_women(
        self, interaction: discord.Interaction, round: int
    ) -> None:
        await self._show_round_lb(interaction, SECTION_WOMEN, round)

    async def _show_round_lb(
        self,
        interaction: discord.Interaction,
        section: str,
        round_number: int,
    ) -> None:
        rows = database.get_round_scores(section, round_number)
        section_label = "Open" if section == SECTION_OPEN else "Women's"

        if not rows:
            await interaction.response.send_message(
                f"No scores yet for {section_label} Round {round_number}.",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title=f"Leaderboard — {section_label} Round {round_number}",
            color=discord.Color.orange(),
            timestamp=datetime.now(timezone.utc),
        )
        lines = []
        for i, row in enumerate(rows, start=1):
            medal = MEDALS[i - 1] if i <= 3 else f"**{i}.**"
            lines.append(
                f"{medal} **{row['username']}** — "
                f"{row['round_points']} pts | "
                f"{row['correct']} correct"
            )
        embed.description = "\n".join(lines)
        await interaction.response.send_message(embed=embed)

    # ------------------------------------------------------------------
    # /mystats
    # ------------------------------------------------------------------

    @app_commands.command(
        name="mystats",
        description="Show your prediction statistics.",
    )
    @app_commands.describe(section="Filter by 'open' or 'women'. Leave blank for combined.")
    async def mystats(
        self,
        interaction: discord.Interaction,
        section: str | None = None,
    ) -> None:
        section_filter = section.lower() if section else None
        await self._show_user_stats(interaction, interaction.user, section_filter, ephemeral=True)

    # ------------------------------------------------------------------
    # /userstats
    # ------------------------------------------------------------------

    @app_commands.command(
        name="userstats",
        description="Show prediction statistics for another user.",
    )
    @app_commands.describe(
        user="The Discord user to look up.",
        section="Filter by 'open' or 'women'. Leave blank for combined.",
    )
    async def userstats(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        section: str | None = None,
    ) -> None:
        section_filter = section.lower() if section else None
        await self._show_user_stats(interaction, user, section_filter, ephemeral=False)

    async def _show_user_stats(
        self,
        interaction: discord.Interaction,
        user: discord.Member | discord.User,
        section: str | None,
        ephemeral: bool,
    ) -> None:
        stats = database.get_user_stats(user.id, section)
        section_label = (
            "Open" if section == SECTION_OPEN
            else "Women's" if section == SECTION_WOMEN
            else "Combined"
        )

        embed = discord.Embed(
            title=f"Stats — {user.display_name} ({section_label})",
            color=discord.Color.blurple(),
            timestamp=datetime.now(timezone.utc),
        )

        if stats is None or stats["games_scored"] is None or stats["games_scored"] == 0:
            embed.description = "No scored predictions yet."
            await interaction.response.send_message(embed=embed, ephemeral=ephemeral)
            return

        accuracy = (
            f"{stats['correct'] / stats['games_scored'] * 100:.1f}%"
            if stats["games_scored"] > 0
            else "—"
        )

        embed.add_field(name="Total Points",      value=str(stats["total_points"] or 0), inline=True)
        embed.add_field(name="Games Scored",      value=str(stats["games_scored"] or 0), inline=True)
        embed.add_field(name="Correct Predictions", value=str(stats["correct"] or 0),   inline=True)
        embed.add_field(name="Accuracy",          value=accuracy,                         inline=True)
        embed.add_field(name="Rounds Played",     value=str(stats["rounds_played"] or 0), inline=True)

        # Rank on leaderboard
        lb = database.get_leaderboard(section)
        rank = next(
            (i + 1 for i, r in enumerate(lb) if r["user_id"] == user.id), None
        )
        if rank:
            embed.add_field(name="Leaderboard Rank", value=f"#{rank}", inline=True)

        # Recent predictions
        recent = database.get_all_predictions_for_user(user.id)
        if section:
            recent = [p for p in recent if p["section"] == section]
        # Only show scored ones
        scored_recent = [p for p in recent if p["result"] is not None][-5:]
        if scored_recent:
            lines = []
            for p in scored_recent:
                correct = "✅" if p["prediction"] == p["result"] else "❌"
                lines.append(
                    f"{correct} R{p['round_number']} #{p['game_id']}: "
                    f"{p['white_player']} vs {p['black_player']} — "
                    f"predicted {RESULT_LABELS.get(p['prediction'], p['prediction'])}"
                )
            embed.add_field(
                name="Recent Scored Predictions",
                value="\n".join(lines),
                inline=False,
            )

        await interaction.response.send_message(embed=embed, ephemeral=ephemeral)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Leaderboard(bot))
