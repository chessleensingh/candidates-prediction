"""
Static tournament data for the 2026 Chess Candidates Tournament.
Pegeia, Cyprus (Cap St Georges Hotel and Resort).
March 29 – April 15, 2026 (14 rounds, double round-robin, 8 players per section)
"""

from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Players
# ---------------------------------------------------------------------------

OPEN_PLAYERS = [
    "Fabiano Caruana",
    "Javokhir Sindarov",
    "Wei Yi",
    "Hikaru Nakamura",
    "Anish Giri",
    "Matthias Bluebaum",
    "Andrey Esipenko",
    "Praggnanandhaa R",
]

WOMEN_PLAYERS = [
    "Zhu Jiner",
    "Aleksandra Goryachkina",
    "Tan Zhongyi",
    "Kateryna Lagno",
    "Vaishali Rameshbabu",
    "Divya Deshmukh",
    "Bibisara Assaubayeva",
    "Anna Muzychuk",
]

# ---------------------------------------------------------------------------
# Round schedule
# All times are UTC. Games start at 12:30 UTC (15:30 EEST / local Cyprus time).
# Predictions close 30 minutes before each round starts (12:00 UTC).
# Rest days: April 2, 6, 10, 13.
# Both sections share the same schedule.
# ---------------------------------------------------------------------------

ROUND_DATES = [
    datetime(2026, 3, 29, 12, 30, tzinfo=timezone.utc),   # R1
    datetime(2026, 3, 30, 12, 30, tzinfo=timezone.utc),   # R2
    datetime(2026, 3, 31, 12, 30, tzinfo=timezone.utc),   # R3
    datetime(2026, 4,  1, 12, 30, tzinfo=timezone.utc),   # R4
    # April 2 = rest day
    datetime(2026, 4,  3, 12, 30, tzinfo=timezone.utc),   # R5
    datetime(2026, 4,  4, 12, 30, tzinfo=timezone.utc),   # R6
    datetime(2026, 4,  5, 12, 30, tzinfo=timezone.utc),   # R7
    # April 6 = rest day
    datetime(2026, 4,  7, 12, 30, tzinfo=timezone.utc),   # R8
    datetime(2026, 4,  8, 12, 30, tzinfo=timezone.utc),   # R9
    datetime(2026, 4,  9, 12, 30, tzinfo=timezone.utc),   # R10
    # April 10 = rest day
    datetime(2026, 4, 11, 12, 30, tzinfo=timezone.utc),   # R11
    datetime(2026, 4, 12, 12, 30, tzinfo=timezone.utc),   # R12
    # April 13 = rest day
    datetime(2026, 4, 14, 12, 30, tzinfo=timezone.utc),   # R13
    datetime(2026, 4, 15, 12, 30, tzinfo=timezone.utc),   # R14
]

# Both sections use the same dates
OPEN_ROUND_DATES = ROUND_DATES
WOMEN_ROUND_DATES = ROUND_DATES

# Prediction cutoff: 30 minutes before round start
PREDICTION_CUTOFF_MINUTES = 30

# ---------------------------------------------------------------------------
# Pairings  (double round-robin, Berger system for 8 players)
# Each round has 4 games.  Tuple: (white_player_index, black_player_index)
# using 0-based index into the relevant players list.
# Generated with the standard Berger round-robin schedule for 8 players.
# ---------------------------------------------------------------------------

def _berger_schedule(n: int) -> list[list[tuple[int, int]]]:
    """
    Generate a single round-robin Berger schedule for n players (n must be even).
    Returns a list of rounds; each round is a list of (home, away) pairs.
    Home plays White in round 1 of each pairing; colours swap in second half.
    """
    players = list(range(n))
    rounds = []
    for r in range(n - 1):
        round_pairs = []
        for i in range(n // 2):
            home = players[i]
            away = players[n - 1 - i]
            if r % 2 == 0:
                round_pairs.append((home, away))
            else:
                round_pairs.append((away, home))
        rounds.append(round_pairs)
        # Rotate: keep player 0 fixed, rotate the rest
        players = [players[0]] + [players[-1]] + players[1:-1]
    return rounds


def _build_pairings(players: list[str]) -> list[list[tuple[str, str]]]:
    """
    Build a full double round-robin pairing list.
    Returns 14 rounds (for 8 players); each round is a list of 4 (white, black) tuples.
    """
    n = len(players)
    first_half = _berger_schedule(n)   # 7 rounds
    # Second half: reverse colours
    second_half = [[(b, w) for w, b in rnd] for rnd in first_half]
    all_rounds = first_half + second_half  # 14 rounds
    # Map indices to names
    named = []
    for rnd in all_rounds:
        named.append([(players[w], players[b]) for w, b in rnd])
    return named


OPEN_PAIRINGS: list[list[tuple[str, str]]] = _build_pairings(OPEN_PLAYERS)
WOMEN_PAIRINGS: list[list[tuple[str, str]]] = _build_pairings(WOMEN_PLAYERS)

# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

# Points awarded for a correct prediction
POINTS_CORRECT = 3
# Bonus points for predicting a decisive result correctly (win/loss, not draw)
POINTS_DECISIVE_BONUS = 1

# Result constants (stored in DB and used in predictions)
RESULT_WHITE_WIN = "1-0"
RESULT_DRAW = "1/2-1/2"
RESULT_BLACK_WIN = "0-1"

VALID_RESULTS = {RESULT_WHITE_WIN, RESULT_DRAW, RESULT_BLACK_WIN}

RESULT_LABELS = {
    RESULT_WHITE_WIN: "White wins",
    RESULT_DRAW: "Draw",
    RESULT_BLACK_WIN: "Black wins",
}

SECTION_OPEN = "open"
SECTION_WOMEN = "women"
VALID_SECTIONS = {SECTION_OPEN, SECTION_WOMEN}
