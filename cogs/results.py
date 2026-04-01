"""
Results cog — admin commands to enter official game results and trigger scoring.

Slash commands (admin only):
  /enterresult <game_id> <result>  — enter a single game result
  /scoreround open <round>         — compute scores for a full round
  /scoreround women <round>        — same for women's section
  /roundresults open <round>       — display results entered so far for a round
"""

import logging
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands, tasks

import database
import config
import scoring as scoring_module
from tournament_data import (
    RESULT_WHITE_WIN,
    RESULT_DRAW,
    RESULT_BLACK_WIN,
    RESULT_LABELS,
    VALID_RESULTS,
    SECTION_OPEN,
    SECTION_WOMEN,
)

log = logging.getLogger(__name__)

RESULT_CHOICES = [
    app_commands.Choice(name="White wins (1-0)",     value=RESULT_WHITE_WIN),
    app_commands.Choice(name="Draw (1/2-1/2)",        value=RESULT_DRAW),
    app_commands.Choice(name="Black wins (0-1)",      value=RESULT_BLACK_WIN),
]

RESULT_EMOJI = {
    RESULT_WHITE_WIN: "⬜",
    RESULT_DRAW:      "🟡",
    RESULT_BLACK_WIN: "⬛",
}


def _is_admin(interaction: discord.Interaction) -> bool:
    """Return True if the user has the configured admin role, or is guild owner."""
    if interaction.guild is None:
        return False
    if interaction.user.id == interaction.guild.owner_id:
        return True
    if config.ADMIN_ROLE_ID:
        role_ids = [r.id for r in interaction.user.roles]
        return config.ADMIN_ROLE_ID in role_ids
    # If no role configured, allow anyone with Manage Guild permission
    return interaction.user.guild_permissions.manage_guild


def _admin_check(interaction: discord.Interaction) -> bool:
    if not _is_admin(interaction):
        raise app_commands.CheckFailure("You need the admin role to use this command.")
    return True


class Results(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.auto_score_task.start()

    def cog_unload(self) -> None:
        self.auto_score_task.cancel()

    # ------------------------------------------------------------------
    # /enterresult
    # ------------------------------------------------------------------

    @app_commands.command(
        name="enterresult",
        description="[Admin] Enter the official result of a game.",
    )
    @app_commands.describe(
        game_id="The numeric game ID (use /roundresults to find it).",
        result="The game result.",
    )
    @app_commands.choices(result=RESULT_CHOICES)
    @app_commands.check(_admin_check)
    async def enterresult(
        self,
        interaction: discord.Interaction,
        game_id: int,
        result: app_commands.Choice[str],
    ) -> None:
        game = database.get_game(game_id)
        if not game:
            await interaction.response.send_message(
                f"No game found with ID {game_id}.", ephemeral=True
            )
            return

        database.save_result(game_id, result.value, interaction.user.id)
        log.info(
            "Admin %s entered result for game %d: %s",
            interaction.user,
            game_id,
            result.value,
        )

        # Auto-score this game immediately
        scored = _score_game(game_id, result.value)
        embed = discord.Embed(
            title=f"Result Entered — Game #{game_id}",
            color=discord.Color.green(),
        )
        embed.add_field(
            name="Game",
            value=f"**{game['white_player']}** vs **{game['black_player']}**",
            inline=False,
        )
        embed.add_field(
            name="Result",
            value=f"{RESULT_EMOJI[result.value]} {result.name}",
            inline=True,
        )
        embed.add_field(
            name="Predictions Scored",
            value=str(len(scored)),
            inline=True,
        )
        await interaction.response.send_message(embed=embed)

        # Post to announcements channel if configured
        if config.ANNOUNCEMENTS_CHANNEL_ID:
            channel = self.bot.get_channel(config.ANNOUNCEMENTS_CHANNEL_ID)
            if channel:
                section_label = (
                    "Open" if game["section"] == SECTION_OPEN else "Women's"
                )
                await channel.send(
                    embed=discord.Embed(
                        title=f"Result: {section_label} R{game['round_number']} Game #{game_id}",
                        description=(
                            f"**{game['white_player']}** vs **{game['black_player']}**\n"
                            f"Result: {RESULT_EMOJI[result.value]} **{result.name}**\n"
                            f"Scored {len(scored)} predictions."
                        ),
                        color=discord.Color.green(),
                    )
                )

    # ------------------------------------------------------------------
    # /scoreround
    # ------------------------------------------------------------------

    score_group = app_commands.Group(
        name="scoreround",
        description="[Admin] Compute scores for all games in a round that have results.",
    )

    @score_group.command(
        name="open",
        description="[Admin] Score all games with results in an Open section round.",
    )
    @app_commands.describe(round="Round number (1-14).")
    @app_commands.check(_admin_check)
    async def scoreround_open(
        self, interaction: discord.Interaction, round: int
    ) -> None:
        await self._score_round(interaction, SECTION_OPEN, round)

    @score_group.command(
        name="women",
        description="[Admin] Score all games with results in a Women's section round.",
    )
    @app_commands.describe(round="Round number (1-14).")
    @app_commands.check(_admin_check)
    async def scoreround_women(
        self, interaction: discord.Interaction, round: int
    ) -> None:
        await self._score_round(interaction, SECTION_WOMEN, round)

    async def _score_round(
        self,
        interaction: discord.Interaction,
        section: str,
        round_number: int,
    ) -> None:
        results = database.get_results_for_round(section, round_number)
        if not results:
            await interaction.response.send_message(
                f"No results entered yet for {section} round {round_number}.",
                ephemeral=True,
            )
            return

        total_scored = 0
        for res in results:
            scored = _score_game(res["game_id"], res["result"])
            total_scored += len(scored)

        section_label = "Open" if section == SECTION_OPEN else "Women's"
        await interaction.response.send_message(
            f"Scored {section_label} Round {round_number}: "
            f"{total_scored} prediction(s) across {len(results)} game(s)."
        )

    # ------------------------------------------------------------------
    # /roundresults
    # ------------------------------------------------------------------

    roundresults_group = app_commands.Group(
        name="roundresults",
        description="Show official results for a round.",
    )

    @roundresults_group.command(
        name="open",
        description="Show game IDs and results for an Open section round.",
    )
    @app_commands.describe(round="Round number (1-14). Defaults to current round.")
    async def roundresults_open(
        self, interaction: discord.Interaction, round: int | None = None
    ) -> None:
        await self._show_roundresults(interaction, SECTION_OPEN, round)

    @roundresults_group.command(
        name="women",
        description="Show game IDs and results for a Women's section round.",
    )
    @app_commands.describe(round="Round number (1-14). Defaults to current round.")
    async def roundresults_women(
        self, interaction: discord.Interaction, round: int | None = None
    ) -> None:
        await self._show_roundresults(interaction, SECTION_WOMEN, round)

    async def _show_roundresults(
        self,
        interaction: discord.Interaction,
        section: str,
        round_number: int | None,
    ) -> None:
        if round_number is None:
            round_number = database.get_current_round(section)

        games = database.get_games_for_round(section, round_number)
        if not games:
            await interaction.response.send_message(
                f"No games found for {section} round {round_number}.", ephemeral=True
            )
            return

        section_label = "Open" if section == SECTION_OPEN else "Women's"
        embed = discord.Embed(
            title=f"{section_label} Round {round_number} — Results",
            color=discord.Color.orange(),
        )
        for g in games:
            result_str = (
                f"{RESULT_EMOJI.get(g['result'], '')} {RESULT_LABELS.get(g['result'], 'Pending')}"
                if g["result"]
                else "⏳ Pending"
            )
            # Prediction distribution
            dist = database.get_prediction_distribution(g["game_id"])
            dist_str = " | ".join(
                f"{RESULT_EMOJI[r]}{dist.get(r, 0)}"
                for r in (RESULT_WHITE_WIN, RESULT_DRAW, RESULT_BLACK_WIN)
            )
            embed.add_field(
                name=f"[#{g['game_id']}] {g['white_player']} vs {g['black_player']}",
                value=f"Result: {result_str}\nPredictions: {dist_str}",
                inline=False,
            )
        await interaction.response.send_message(embed=embed)

    # ------------------------------------------------------------------
    # Error handler
    # ------------------------------------------------------------------

    @enterresult.error
    @scoreround_open.error
    @scoreround_women.error
    async def admin_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ) -> None:
        if isinstance(error, app_commands.CheckFailure):
            await interaction.response.send_message(
                "You do not have permission to use this command.", ephemeral=True
            )
        else:
            log.error("Admin command error: %s", error, exc_info=True)
            await interaction.response.send_message(
                "An error occurred.", ephemeral=True
            )

    # ------------------------------------------------------------------
    # Background task: auto-score when results are entered
    # ------------------------------------------------------------------

    @tasks.loop(seconds=config.BACKGROUND_TASK_INTERVAL)
    async def auto_score_task(self) -> None:
        """
        Every N seconds, check if any games have results but unscored predictions,
        and score them automatically.
        """
        try:
            _auto_score_pending()
        except Exception as exc:
            log.error("auto_score_task error: %s", exc, exc_info=True)

    @auto_score_task.before_loop
    async def before_auto_score(self) -> None:
        await self.bot.wait_until_ready()


# ---------------------------------------------------------------------------
# Internal scoring helpers
# ---------------------------------------------------------------------------

def _score_game(game_id: int, result: str) -> list[dict]:
    """Fetch predictions for a game and write scores. Returns scored items."""
    import sqlite3
    # Get all predictions for this game
    with database._conn() as con:
        preds = con.execute(
            "SELECT user_id, game_id, prediction FROM predictions WHERE game_id = ?",
            (game_id,),
        ).fetchall()

    scored = []
    for pred in preds:
        points = scoring_module.calculate_points(pred["prediction"], result)
        database.save_score(
            user_id=pred["user_id"],
            game_id=game_id,
            prediction=pred["prediction"],
            actual=result,
            points=points,
        )
        scored.append(
            {
                "user_id": pred["user_id"],
                "game_id": game_id,
                "prediction": pred["prediction"],
                "actual": result,
                "points": points,
            }
        )
    return scored


def _auto_score_pending() -> None:
    """Score any games that have results but not yet scored predictions."""
    with database._conn() as con:
        # Find games with results where any prediction is not yet in scores
        pending = con.execute(
            """
            SELECT DISTINCT p.game_id, r.result
            FROM predictions p
            JOIN results r USING (game_id)
            WHERE NOT EXISTS (
                SELECT 1 FROM scores s
                WHERE s.user_id = p.user_id AND s.game_id = p.game_id
            )
            """
        ).fetchall()

    for row in pending:
        _score_game(row["game_id"], row["result"])
        log.info("Auto-scored game %d", row["game_id"])


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Results(bot))
