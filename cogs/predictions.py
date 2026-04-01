"""
Prediction cog — lets users submit predictions for individual games.

Slash commands:
  /predict open <round>   — show buttons to predict every game in an open round
  /predict women <round>  — same for the women's section
  /mypredictions          — show all predictions the caller has made
  /predictionstatus       — show how many people have predicted each round
"""

import logging
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands

import database
import config
from tournament_data import (
    RESULT_WHITE_WIN,
    RESULT_DRAW,
    RESULT_BLACK_WIN,
    RESULT_LABELS,
    SECTION_OPEN,
    SECTION_WOMEN,
    VALID_RESULTS,
)

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helper: result choice → label
# ---------------------------------------------------------------------------

RESULT_EMOJI = {
    RESULT_WHITE_WIN: "⬜",
    RESULT_DRAW:      "🟡",
    RESULT_BLACK_WIN: "⬛",
}


def _result_display(result: str) -> str:
    return f"{RESULT_EMOJI.get(result, '')} {RESULT_LABELS.get(result, result)}"


# ---------------------------------------------------------------------------
# Select-menu view for predicting a single round
# ---------------------------------------------------------------------------

class GamePredictionSelect(discord.ui.Select):
    """A single dropdown for one game."""

    def __init__(
        self,
        game_id: int,
        white: str,
        black: str,
        existing_prediction: str | None,
    ) -> None:
        self.game_id = game_id
        options = [
            discord.SelectOption(
                label=f"White wins ({white})",
                value=RESULT_WHITE_WIN,
                emoji="⬜",
                default=(existing_prediction == RESULT_WHITE_WIN),
            ),
            discord.SelectOption(
                label="Draw",
                value=RESULT_DRAW,
                emoji="🟡",
                default=(existing_prediction == RESULT_DRAW),
            ),
            discord.SelectOption(
                label=f"Black wins ({black})",
                value=RESULT_BLACK_WIN,
                emoji="⬛",
                default=(existing_prediction == RESULT_BLACK_WIN),
            ),
        ]
        super().__init__(
            placeholder=f"{white} vs {black}",
            options=options,
            min_values=1,
            max_values=1,
            custom_id=f"predict:{game_id}",
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        selected = self.values[0]
        user = interaction.user

        if not database.is_predictions_open(self.game_id):
            await interaction.response.send_message(
                "Predictions are closed for this game.", ephemeral=True
            )
            return

        database.upsert_user(user.id, str(user))
        database.save_prediction(user.id, self.game_id, selected)
        log.info(
            "User %s predicted game %d: %s", user, self.game_id, selected
        )
        await interaction.response.send_message(
            f"Prediction saved: **{_result_display(selected)}** for game #{self.game_id}.",
            ephemeral=True,
        )


class RoundPredictionView(discord.ui.View):
    """A view with one dropdown per game in a round."""

    def __init__(
        self,
        games: list,
        user_id: int,
    ) -> None:
        super().__init__(timeout=300)
        for game in games:
            existing = database.get_prediction(user_id, game["game_id"])
            pred = existing["prediction"] if existing else None
            self.add_item(
                GamePredictionSelect(
                    game_id=game["game_id"],
                    white=game["white_player"],
                    black=game["black_player"],
                    existing_prediction=pred,
                )
            )


# ---------------------------------------------------------------------------
# Cog
# ---------------------------------------------------------------------------

class Predictions(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    # ------------------------------------------------------------------
    # /predict
    # ------------------------------------------------------------------

    predict_group = app_commands.Group(
        name="predict",
        description="Submit predictions for a round of the Candidates Tournament.",
    )

    @predict_group.command(name="open", description="Predict results for a round in the Open section.")
    @app_commands.describe(round="Round number (1-14). Defaults to the current/next round.")
    async def predict_open(
        self, interaction: discord.Interaction, round: int | None = None
    ) -> None:
        await self._predict(interaction, SECTION_OPEN, round)

    @predict_group.command(name="women", description="Predict results for a round in the Women's section.")
    @app_commands.describe(round="Round number (1-14). Defaults to the current/next round.")
    async def predict_women(
        self, interaction: discord.Interaction, round: int | None = None
    ) -> None:
        await self._predict(interaction, SECTION_WOMEN, round)

    async def _predict(
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
                f"No games found for {section} round {round_number}.",
                ephemeral=True,
            )
            return

        # Check if any game is still open
        now_iso = datetime.now(timezone.utc).isoformat()
        open_games = [g for g in games if g["cutoff_utc"] > now_iso]
        if not open_games:
            await interaction.response.send_message(
                f"Predictions are **closed** for {section.capitalize()} Round {round_number}. "
                "Results are being awaited.",
                ephemeral=True,
            )
            return

        section_label = "Open" if section == SECTION_OPEN else "Women's"
        embed = discord.Embed(
            title=f"2026 Candidates — {section_label} Round {round_number}",
            description=(
                "Select your prediction for each game below.\n"
                "You can change your prediction until the round starts.\n\n"
                f"**Predictions close:** <t:{_cutoff_ts(open_games[0]['cutoff_utc'])}:R>"
            ),
            color=discord.Color.gold(),
        )
        for g in games:
            status = ""
            if g["cutoff_utc"] <= now_iso:
                status = " *(closed)*"
            embed.add_field(
                name=f"Game #{g['game_id']}{status}",
                value=f"⬜ **{g['white_player']}** vs **{g['black_player']}** ⬛",
                inline=False,
            )

        view = RoundPredictionView(games=open_games, user_id=interaction.user.id)
        await interaction.response.send_message(
            embed=embed, view=view, ephemeral=True
        )

    # ------------------------------------------------------------------
    # /mypredictions
    # ------------------------------------------------------------------

    @app_commands.command(
        name="mypredictions",
        description="See all the predictions you have made.",
    )
    @app_commands.describe(section="Filter by section: 'open' or 'women'. Leave blank for all.")
    async def mypredictions(
        self,
        interaction: discord.Interaction,
        section: str | None = None,
    ) -> None:
        user = interaction.user
        preds = database.get_all_predictions_for_user(user.id)

        if section:
            section = section.lower()
            preds = [p for p in preds if p["section"] == section]

        if not preds:
            await interaction.response.send_message(
                "You have not made any predictions yet.", ephemeral=True
            )
            return

        # Group by section + round
        grouped: dict[tuple[str, int], list] = {}
        for p in preds:
            key = (p["section"], p["round_number"])
            grouped.setdefault(key, []).append(p)

        embeds = []
        current_embed = discord.Embed(
            title=f"Your Predictions — {user.display_name}",
            color=discord.Color.blurple(),
        )
        field_count = 0

        for (sec, rnd), games in sorted(grouped.items()):
            section_label = "Open" if sec == SECTION_OPEN else "Women's"
            lines = []
            for p in games:
                pred_icon = RESULT_EMOJI.get(p["prediction"], "?")
                actual_icon = ""
                correct = ""
                if p["result"]:
                    actual_icon = RESULT_EMOJI.get(p["result"], "?")
                    correct = " ✅" if p["prediction"] == p["result"] else " ❌"
                lines.append(
                    f"{pred_icon} **{p['white_player']}** vs **{p['black_player']}**"
                    f"{(' → ' + actual_icon) if actual_icon else ''}{correct}"
                )

            if field_count >= 24:
                embeds.append(current_embed)
                current_embed = discord.Embed(color=discord.Color.blurple())
                field_count = 0

            current_embed.add_field(
                name=f"{section_label} R{rnd}",
                value="\n".join(lines),
                inline=False,
            )
            field_count += 1

        embeds.append(current_embed)
        await interaction.response.send_message(
            embeds=embeds[:10], ephemeral=True
        )

    # ------------------------------------------------------------------
    # /predictionstatus
    # ------------------------------------------------------------------

    @app_commands.command(
        name="predictionstatus",
        description="See how many predictions have been submitted per round.",
    )
    async def predictionstatus(self, interaction: discord.Interaction) -> None:
        embed = discord.Embed(
            title="Prediction Status",
            description="Number of predictions submitted per round.",
            color=discord.Color.blue(),
        )
        for section in (SECTION_OPEN, SECTION_WOMEN):
            section_label = "Open" if section == SECTION_OPEN else "Women's"
            lines = []
            for rnd in range(1, 15):
                games = database.get_games_for_round(section, rnd)
                if not games:
                    continue
                counts = database.count_predictions_for_round(section, rnd)
                total_pred = sum(counts.values())
                n_games = len(games)
                lines.append(f"R{rnd}: {total_pred} predictions across {n_games} games")
            embed.add_field(
                name=section_label,
                value="\n".join(lines) if lines else "No data",
                inline=False,
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def _cutoff_ts(cutoff_iso: str) -> int:
    """Convert ISO string to Unix timestamp integer for Discord <t:> format."""
    dt = datetime.fromisoformat(cutoff_iso)
    return int(dt.timestamp())


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Predictions(bot))
