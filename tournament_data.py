"""
Static tournament data for the 2026 Chess Candidates Tournament.
Pegeia, Cyprus (Cap St Georges Hotel and Resort).
March 29 – April 15, 2026 (14 rounds, double round-robin, 8 players per section)
Pairings sourced from: lichess.org/broadcast/fide-candidates-2026--combined-open--women
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

OPEN_ROUND_DATES = ROUND_DATES
WOMEN_ROUND_DATES = ROUND_DATES

PREDICTION_CUTOFF_MINUTES = 30

# ---------------------------------------------------------------------------
# Official pairings — sourced from Lichess broadcast
# Each entry is (white_player, black_player)
# ---------------------------------------------------------------------------

OPEN_PAIRINGS: list[list[tuple[str, str]]] = [
    # R1
    [("Fabiano Caruana", "Hikaru Nakamura"),
     ("Praggnanandhaa R", "Anish Giri"),
     ("Matthias Bluebaum", "Wei Yi"),
     ("Javokhir Sindarov", "Andrey Esipenko")],
    # R2
    [("Andrey Esipenko", "Hikaru Nakamura"),
     ("Anish Giri", "Fabiano Caruana"),
     ("Wei Yi", "Praggnanandhaa R"),
     ("Javokhir Sindarov", "Matthias Bluebaum")],
    # R3
    [("Matthias Bluebaum", "Andrey Esipenko"),
     ("Praggnanandhaa R", "Javokhir Sindarov"),
     ("Fabiano Caruana", "Wei Yi"),
     ("Hikaru Nakamura", "Anish Giri")],
    # R4
    [("Andrey Esipenko", "Anish Giri"),
     ("Wei Yi", "Hikaru Nakamura"),
     ("Javokhir Sindarov", "Fabiano Caruana"),
     ("Matthias Bluebaum", "Praggnanandhaa R")],
    # R5
    [("Praggnanandhaa R", "Andrey Esipenko"),
     ("Fabiano Caruana", "Matthias Bluebaum"),
     ("Hikaru Nakamura", "Javokhir Sindarov"),
     ("Anish Giri", "Wei Yi")],
    # R6
    [("Fabiano Caruana", "Andrey Esipenko"),
     ("Hikaru Nakamura", "Praggnanandhaa R"),
     ("Anish Giri", "Matthias Bluebaum"),
     ("Wei Yi", "Javokhir Sindarov")],
    # R7
    [("Andrey Esipenko", "Wei Yi"),
     ("Javokhir Sindarov", "Anish Giri"),
     ("Matthias Bluebaum", "Hikaru Nakamura"),
     ("Praggnanandhaa R", "Fabiano Caruana")],
    # R8
    [("Andrey Esipenko", "Javokhir Sindarov"),
     ("Wei Yi", "Matthias Bluebaum"),
     ("Anish Giri", "Praggnanandhaa R"),
     ("Hikaru Nakamura", "Fabiano Caruana")],
    # R9
    [("Hikaru Nakamura", "Andrey Esipenko"),
     ("Fabiano Caruana", "Anish Giri"),
     ("Praggnanandhaa R", "Wei Yi"),
     ("Matthias Bluebaum", "Javokhir Sindarov")],
    # R10
    [("Andrey Esipenko", "Matthias Bluebaum"),
     ("Javokhir Sindarov", "Praggnanandhaa R"),
     ("Wei Yi", "Fabiano Caruana"),
     ("Anish Giri", "Hikaru Nakamura")],
    # R11
    [("Anish Giri", "Andrey Esipenko"),
     ("Hikaru Nakamura", "Wei Yi"),
     ("Fabiano Caruana", "Javokhir Sindarov"),
     ("Praggnanandhaa R", "Matthias Bluebaum")],
    # R12
    [("Andrey Esipenko", "Praggnanandhaa R"),
     ("Matthias Bluebaum", "Fabiano Caruana"),
     ("Javokhir Sindarov", "Hikaru Nakamura"),
     ("Wei Yi", "Anish Giri")],
    # R13
    [("Wei Yi", "Andrey Esipenko"),
     ("Anish Giri", "Javokhir Sindarov"),
     ("Hikaru Nakamura", "Matthias Bluebaum"),
     ("Fabiano Caruana", "Praggnanandhaa R")],
    # R14
    [("Andrey Esipenko", "Fabiano Caruana"),
     ("Praggnanandhaa R", "Hikaru Nakamura"),
     ("Matthias Bluebaum", "Anish Giri"),
     ("Javokhir Sindarov", "Wei Yi")],
]

WOMEN_PAIRINGS: list[list[tuple[str, str]]] = [
    # R1
    [("Divya Deshmukh", "Anna Muzychuk"),
     ("Vaishali Rameshbabu", "Bibisara Assaubayeva"),
     ("Aleksandra Goryachkina", "Kateryna Lagno"),
     ("Zhu Jiner", "Tan Zhongyi")],
    # R2
    [("Anna Muzychuk", "Tan Zhongyi"),
     ("Kateryna Lagno", "Zhu Jiner"),
     ("Bibisara Assaubayeva", "Aleksandra Goryachkina"),
     ("Divya Deshmukh", "Vaishali Rameshbabu")],
    # R3
    [("Vaishali Rameshbabu", "Anna Muzychuk"),
     ("Aleksandra Goryachkina", "Divya Deshmukh"),
     ("Zhu Jiner", "Bibisara Assaubayeva"),
     ("Tan Zhongyi", "Kateryna Lagno")],
    # R4
    [("Anna Muzychuk", "Kateryna Lagno"),
     ("Bibisara Assaubayeva", "Tan Zhongyi"),
     ("Divya Deshmukh", "Zhu Jiner"),
     ("Vaishali Rameshbabu", "Aleksandra Goryachkina")],
    # R5
    [("Aleksandra Goryachkina", "Anna Muzychuk"),
     ("Zhu Jiner", "Vaishali Rameshbabu"),
     ("Tan Zhongyi", "Divya Deshmukh"),
     ("Kateryna Lagno", "Bibisara Assaubayeva")],
    # R6
    [("Zhu Jiner", "Anna Muzychuk"),
     ("Tan Zhongyi", "Aleksandra Goryachkina"),
     ("Kateryna Lagno", "Vaishali Rameshbabu"),
     ("Bibisara Assaubayeva", "Divya Deshmukh")],
    # R7
    [("Anna Muzychuk", "Bibisara Assaubayeva"),
     ("Divya Deshmukh", "Kateryna Lagno"),
     ("Vaishali Rameshbabu", "Tan Zhongyi"),
     ("Aleksandra Goryachkina", "Zhu Jiner")],
    # R8
    [("Anna Muzychuk", "Divya Deshmukh"),
     ("Bibisara Assaubayeva", "Vaishali Rameshbabu"),
     ("Kateryna Lagno", "Aleksandra Goryachkina"),
     ("Tan Zhongyi", "Zhu Jiner")],
    # R9
    [("Tan Zhongyi", "Anna Muzychuk"),
     ("Zhu Jiner", "Kateryna Lagno"),
     ("Aleksandra Goryachkina", "Bibisara Assaubayeva"),
     ("Vaishali Rameshbabu", "Divya Deshmukh")],
    # R10
    [("Anna Muzychuk", "Vaishali Rameshbabu"),
     ("Divya Deshmukh", "Aleksandra Goryachkina"),
     ("Bibisara Assaubayeva", "Zhu Jiner"),
     ("Kateryna Lagno", "Tan Zhongyi")],
    # R11
    [("Kateryna Lagno", "Anna Muzychuk"),
     ("Tan Zhongyi", "Bibisara Assaubayeva"),
     ("Zhu Jiner", "Divya Deshmukh"),
     ("Aleksandra Goryachkina", "Vaishali Rameshbabu")],
    # R12
    [("Anna Muzychuk", "Aleksandra Goryachkina"),
     ("Vaishali Rameshbabu", "Zhu Jiner"),
     ("Divya Deshmukh", "Tan Zhongyi"),
     ("Bibisara Assaubayeva", "Kateryna Lagno")],
    # R13
    [("Bibisara Assaubayeva", "Anna Muzychuk"),
     ("Kateryna Lagno", "Divya Deshmukh"),
     ("Tan Zhongyi", "Vaishali Rameshbabu"),
     ("Zhu Jiner", "Aleksandra Goryachkina")],
    # R14
    [("Anna Muzychuk", "Zhu Jiner"),
     ("Aleksandra Goryachkina", "Tan Zhongyi"),
     ("Vaishali Rameshbabu", "Kateryna Lagno"),
     ("Divya Deshmukh", "Bibisara Assaubayeva")],
]

# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

POINTS_CORRECT = 3
POINTS_DECISIVE_BONUS = 1

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
