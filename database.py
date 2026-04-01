"""
SQLite database layer for the Candidates Prediction bot.

All SQL lives here; cogs import functions from this module only.

Schema
------
users            - discord user registry
games            - every game in the tournament (both sections)
predictions      - one row per user per game
results          - official results entered by admin
scores           - computed points per user per game (materialised for speed)
"""

import sqlite3
import logging
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from tournament_data import (
    OPEN_PAIRINGS,
    WOMEN_PAIRINGS,
    OPEN_ROUND_DATES,
    WOMEN_ROUND_DATES,
    OPEN_PLAYERS,
    WOMEN_PLAYERS,
    SECTION_OPEN,
    SECTION_WOMEN,
    PREDICTION_CUTOFF_MINUTES,
)

log = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent / "predictions.db"


@contextmanager
def _conn():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA foreign_keys=ON")
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------

def init_db() -> None:
    """Create all tables and seed static tournament data."""
    with _conn() as con:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id     INTEGER PRIMARY KEY,
                username    TEXT    NOT NULL,
                joined_at   TEXT    NOT NULL
            );

            CREATE TABLE IF NOT EXISTS games (
                game_id         INTEGER PRIMARY KEY AUTOINCREMENT,
                section         TEXT    NOT NULL,   -- 'open' | 'women'
                round_number    INTEGER NOT NULL,
                white_player    TEXT    NOT NULL,
                black_player    TEXT    NOT NULL,
                round_start_utc TEXT    NOT NULL,   -- ISO-8601
                cutoff_utc      TEXT    NOT NULL    -- ISO-8601, predictions close
            );

            CREATE TABLE IF NOT EXISTS predictions (
                prediction_id   INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         INTEGER NOT NULL REFERENCES users(user_id),
                game_id         INTEGER NOT NULL REFERENCES games(game_id),
                prediction      TEXT    NOT NULL,   -- '1-0' | '1/2-1/2' | '0-1'
                submitted_at    TEXT    NOT NULL,
                UNIQUE(user_id, game_id)             -- one prediction per game
            );

            CREATE TABLE IF NOT EXISTS results (
                game_id     INTEGER PRIMARY KEY REFERENCES games(game_id),
                result      TEXT    NOT NULL,        -- '1-0' | '1/2-1/2' | '0-1'
                entered_by  INTEGER,                 -- admin user_id
                entered_at  TEXT    NOT NULL
            );

            CREATE TABLE IF NOT EXISTS scores (
                score_id    INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL REFERENCES users(user_id),
                game_id     INTEGER NOT NULL REFERENCES games(game_id),
                prediction  TEXT    NOT NULL,
                actual      TEXT    NOT NULL,
                points      INTEGER NOT NULL,
                UNIQUE(user_id, game_id)
            );
            """
        )
        _seed_games(con)


def _seed_games(con: sqlite3.Connection) -> None:
    """Insert game rows if they don't exist yet."""
    existing = con.execute("SELECT COUNT(*) FROM games").fetchone()[0]
    if existing > 0:
        return

    rows = []
    for section, pairings, dates in (
        (SECTION_OPEN, OPEN_PAIRINGS, OPEN_ROUND_DATES),
        (SECTION_WOMEN, WOMEN_PAIRINGS, WOMEN_ROUND_DATES),
    ):
        for round_idx, (round_pairings, round_dt) in enumerate(
            zip(pairings, dates), start=1
        ):
            from datetime import timedelta
            cutoff_dt = round_dt - timedelta(minutes=PREDICTION_CUTOFF_MINUTES)
            for white, black in round_pairings:
                rows.append(
                    (
                        section,
                        round_idx,
                        white,
                        black,
                        round_dt.isoformat(),
                        cutoff_dt.isoformat(),
                    )
                )

    con.executemany(
        """
        INSERT INTO games
            (section, round_number, white_player, black_player,
             round_start_utc, cutoff_utc)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    log.info("Seeded %d games into the database.", len(rows))


# ---------------------------------------------------------------------------
# User helpers
# ---------------------------------------------------------------------------

def upsert_user(user_id: int, username: str) -> None:
    with _conn() as con:
        con.execute(
            """
            INSERT INTO users (user_id, username, joined_at)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET username = excluded.username
            """,
            (user_id, username, datetime.now(timezone.utc).isoformat()),
        )


def get_user(user_id: int) -> sqlite3.Row | None:
    with _conn() as con:
        return con.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()


# ---------------------------------------------------------------------------
# Game queries
# ---------------------------------------------------------------------------

def get_games_for_round(section: str, round_number: int) -> list[sqlite3.Row]:
    with _conn() as con:
        return con.execute(
            """
            SELECT g.*, r.result
            FROM games g
            LEFT JOIN results r USING (game_id)
            WHERE g.section = ? AND g.round_number = ?
            ORDER BY g.game_id
            """,
            (section, round_number),
        ).fetchall()


def get_game(game_id: int) -> sqlite3.Row | None:
    with _conn() as con:
        return con.execute(
            "SELECT * FROM games WHERE game_id = ?", (game_id,)
        ).fetchone()


def get_all_games(section: str) -> list[sqlite3.Row]:
    with _conn() as con:
        return con.execute(
            """
            SELECT g.*, r.result
            FROM games g
            LEFT JOIN results r USING (game_id)
            WHERE g.section = ?
            ORDER BY g.round_number, g.game_id
            """,
            (section,),
        ).fetchall()


def get_current_round(section: str) -> int:
    """
    Return the round number that is currently open for predictions,
    or the next upcoming round, or the last round if tournament is over.
    'Current' means: the earliest round whose cutoff_utc is in the future.
    """
    now = datetime.now(timezone.utc).isoformat()
    with _conn() as con:
        row = con.execute(
            """
            SELECT MIN(round_number) as rn
            FROM games
            WHERE section = ? AND cutoff_utc > ?
            """,
            (section, now),
        ).fetchone()
        if row and row["rn"] is not None:
            return row["rn"]
        # Tournament over — return the last round
        row2 = con.execute(
            "SELECT MAX(round_number) as rn FROM games WHERE section = ?",
            (section,),
        ).fetchone()
        return row2["rn"] if row2 else 1


def is_predictions_open(game_id: int) -> bool:
    """Return True if the prediction window is still open for this game."""
    now = datetime.now(timezone.utc).isoformat()
    with _conn() as con:
        row = con.execute(
            "SELECT cutoff_utc FROM games WHERE game_id = ?", (game_id,)
        ).fetchone()
        if row is None:
            return False
        return row["cutoff_utc"] > now


def get_next_round_info(section: str) -> sqlite3.Row | None:
    """Return the first game of the next unpredicted round (for schedule display)."""
    now = datetime.now(timezone.utc).isoformat()
    with _conn() as con:
        return con.execute(
            """
            SELECT * FROM games
            WHERE section = ? AND round_start_utc > ?
            ORDER BY round_start_utc ASC
            LIMIT 1
            """,
            (section, now),
        ).fetchone()


# ---------------------------------------------------------------------------
# Prediction helpers
# ---------------------------------------------------------------------------

def save_prediction(user_id: int, game_id: int, prediction: str) -> None:
    with _conn() as con:
        con.execute(
            """
            INSERT INTO predictions (user_id, game_id, prediction, submitted_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, game_id) DO UPDATE
                SET prediction   = excluded.prediction,
                    submitted_at = excluded.submitted_at
            """,
            (user_id, game_id, prediction, datetime.now(timezone.utc).isoformat()),
        )


def get_prediction(user_id: int, game_id: int) -> sqlite3.Row | None:
    with _conn() as con:
        return con.execute(
            "SELECT * FROM predictions WHERE user_id = ? AND game_id = ?",
            (user_id, game_id),
        ).fetchone()


def get_predictions_for_round(
    section: str, round_number: int, user_id: int | None = None
) -> list[sqlite3.Row]:
    with _conn() as con:
        if user_id:
            return con.execute(
                """
                SELECT p.*, g.white_player, g.black_player, g.round_number,
                       g.section, r.result
                FROM predictions p
                JOIN games g USING (game_id)
                LEFT JOIN results r USING (game_id)
                WHERE g.section = ? AND g.round_number = ? AND p.user_id = ?
                ORDER BY g.game_id
                """,
                (section, round_number, user_id),
            ).fetchall()
        return con.execute(
            """
            SELECT p.*, g.white_player, g.black_player, g.round_number,
                   g.section, r.result
            FROM predictions p
            JOIN games g USING (game_id)
            LEFT JOIN results r USING (game_id)
            WHERE g.section = ? AND g.round_number = ?
            ORDER BY g.game_id, p.user_id
            """,
            (section, round_number),
        ).fetchall()


def get_all_predictions_for_user(user_id: int) -> list[sqlite3.Row]:
    with _conn() as con:
        return con.execute(
            """
            SELECT p.*, g.white_player, g.black_player, g.round_number,
                   g.section, r.result
            FROM predictions p
            JOIN games g USING (game_id)
            LEFT JOIN results r USING (game_id)
            WHERE p.user_id = ?
            ORDER BY g.section, g.round_number, g.game_id
            """,
            (user_id,),
        ).fetchall()


def count_predictions_for_round(section: str, round_number: int) -> dict:
    """Return {game_id: count_of_predictions} for a round."""
    with _conn() as con:
        rows = con.execute(
            """
            SELECT p.game_id, COUNT(*) as cnt
            FROM predictions p
            JOIN games g USING (game_id)
            WHERE g.section = ? AND g.round_number = ?
            GROUP BY p.game_id
            """,
            (section, round_number),
        ).fetchall()
        return {r["game_id"]: r["cnt"] for r in rows}


# ---------------------------------------------------------------------------
# Result helpers
# ---------------------------------------------------------------------------

def save_result(game_id: int, result: str, admin_user_id: int) -> None:
    with _conn() as con:
        con.execute(
            """
            INSERT INTO results (game_id, result, entered_by, entered_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(game_id) DO UPDATE
                SET result     = excluded.result,
                    entered_by = excluded.entered_by,
                    entered_at = excluded.entered_at
            """,
            (game_id, result, admin_user_id, datetime.now(timezone.utc).isoformat()),
        )


def get_result(game_id: int) -> sqlite3.Row | None:
    with _conn() as con:
        return con.execute(
            "SELECT * FROM results WHERE game_id = ?", (game_id,)
        ).fetchone()


def get_results_for_round(section: str, round_number: int) -> list[sqlite3.Row]:
    with _conn() as con:
        return con.execute(
            """
            SELECT r.*
            FROM results r
            JOIN games g USING (game_id)
            WHERE g.section = ? AND g.round_number = ?
            """,
            (section, round_number),
        ).fetchall()


# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------

def save_score(
    user_id: int,
    game_id: int,
    prediction: str,
    actual: str,
    points: int,
) -> None:
    with _conn() as con:
        con.execute(
            """
            INSERT INTO scores (user_id, game_id, prediction, actual, points)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id, game_id) DO UPDATE
                SET prediction = excluded.prediction,
                    actual     = excluded.actual,
                    points     = excluded.points
            """,
            (user_id, game_id, prediction, actual, points),
        )


def get_leaderboard(section: str | None = None) -> list[sqlite3.Row]:
    """
    Return users sorted by total points descending.
    Optionally filter by section.
    """
    with _conn() as con:
        if section:
            return con.execute(
                """
                SELECT u.username, u.user_id,
                       SUM(s.points)  AS total_points,
                       COUNT(s.score_id) AS games_scored,
                       SUM(CASE WHEN s.points > 0 THEN 1 ELSE 0 END) AS correct
                FROM scores s
                JOIN users u USING (user_id)
                JOIN games g ON s.game_id = g.game_id
                WHERE g.section = ?
                GROUP BY u.user_id
                ORDER BY total_points DESC, correct DESC
                """,
                (section,),
            ).fetchall()
        return con.execute(
            """
            SELECT u.username, u.user_id,
                   SUM(s.points)  AS total_points,
                   COUNT(s.score_id) AS games_scored,
                   SUM(CASE WHEN s.points > 0 THEN 1 ELSE 0 END) AS correct
            FROM scores s
            JOIN users u USING (user_id)
            GROUP BY u.user_id
            ORDER BY total_points DESC, correct DESC
            """,
        ).fetchall()


def get_user_stats(user_id: int, section: str | None = None) -> sqlite3.Row | None:
    with _conn() as con:
        if section:
            return con.execute(
                """
                SELECT u.username,
                       SUM(s.points) AS total_points,
                       COUNT(s.score_id) AS games_scored,
                       SUM(CASE WHEN s.points > 0 THEN 1 ELSE 0 END) AS correct,
                       COUNT(DISTINCT g.round_number) AS rounds_played
                FROM scores s
                JOIN users u USING (user_id)
                JOIN games g ON s.game_id = g.game_id
                WHERE s.user_id = ? AND g.section = ?
                """,
                (user_id, section),
            ).fetchone()
        return con.execute(
            """
            SELECT u.username,
                   SUM(s.points) AS total_points,
                   COUNT(s.score_id) AS games_scored,
                   SUM(CASE WHEN s.points > 0 THEN 1 ELSE 0 END) AS correct,
                   COUNT(DISTINCT g.round_number) AS rounds_played
            FROM scores s
            JOIN users u USING (user_id)
            JOIN games g ON s.game_id = g.game_id
            WHERE s.user_id = ?
            """,
            (user_id,),
        ).fetchone()


def get_round_scores(section: str, round_number: int) -> list[sqlite3.Row]:
    """Points earned in a specific round, sorted descending."""
    with _conn() as con:
        return con.execute(
            """
            SELECT u.username, SUM(s.points) AS round_points,
                   SUM(CASE WHEN s.points > 0 THEN 1 ELSE 0 END) AS correct
            FROM scores s
            JOIN users u USING (user_id)
            JOIN games g ON s.game_id = g.game_id
            WHERE g.section = ? AND g.round_number = ?
            GROUP BY u.user_id
            ORDER BY round_points DESC
            """,
            (section, round_number),
        ).fetchall()


def get_prediction_distribution(game_id: int) -> dict:
    """Return how many users predicted each result for a game."""
    with _conn() as con:
        rows = con.execute(
            """
            SELECT prediction, COUNT(*) as cnt
            FROM predictions
            WHERE game_id = ?
            GROUP BY prediction
            """,
            (game_id,),
        ).fetchall()
        return {r["prediction"]: r["cnt"] for r in rows}
