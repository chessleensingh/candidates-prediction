"""
Fetches game results from the Lichess broadcast API.

Configure via env vars:
  LICHESS_OPEN_BROADCAST_ID   — broadcast tournament ID for the Open section
  LICHESS_WOMEN_BROADCAST_ID  — broadcast tournament ID for the Women's section

Broadcast IDs are the short alphanumeric codes in Lichess broadcast URLs:
  lichess.org/broadcast/some-slug/{broadcastTournamentId}
"""

import json
import logging
import re
import urllib.request
from typing import Optional

from tournament_data import OPEN_PLAYERS, WOMEN_PLAYERS

log = logging.getLogger(__name__)

LICHESS_API = "https://lichess.org/api"


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

def _fetch(url: str) -> Optional[str]:
    try:
        req = urllib.request.Request(
            url,
            headers={"Accept": "application/x-ndjson", "User-Agent": "CandidatesPredBot/1.0"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8")
    except Exception as exc:
        log.error("Lichess fetch error %s: %s", url, exc)
        return None


# ---------------------------------------------------------------------------
# Broadcast round lookup
# ---------------------------------------------------------------------------

def get_rounds(broadcast_id: str) -> list[dict]:
    """Return list of round dicts from Lichess for a broadcast tournament."""
    data = _fetch(f"{LICHESS_API}/broadcast/{broadcast_id}")
    if not data:
        return []
    try:
        obj = json.loads(data)
        return obj.get("rounds", [])
    except Exception as exc:
        log.error("Failed to parse broadcast JSON: %s", exc)
        return []


def get_round_results(round_id: str) -> list[dict]:
    """
    Fetch PGN for a broadcast round and return completed games as:
      [{"white": "Full Name", "black": "Full Name", "result": "1-0"|"1/2-1/2"|"0-1"}, ...]
    """
    pgn_text = _fetch(f"{LICHESS_API}/broadcast/round/{round_id}/games")
    if not pgn_text:
        return []
    return _parse_pgn(pgn_text)


# ---------------------------------------------------------------------------
# PGN parsing
# ---------------------------------------------------------------------------

def _header(pgn_block: str, tag: str) -> Optional[str]:
    m = re.search(rf'\[{tag} "([^"]+)"\]', pgn_block)
    return m.group(1) if m else None


def _parse_pgn(pgn_text: str) -> list[dict]:
    games = []
    for block in re.split(r"\n\n(?=\[)", pgn_text.strip()):
        white = _header(block, "White")
        black = _header(block, "Black")
        result = _header(block, "Result")
        if white and black and result and result != "*":
            games.append({"white": white, "black": black, "result": result})
    return games


# ---------------------------------------------------------------------------
# Player name matching
# ---------------------------------------------------------------------------

def _match_player(lichess_name: str, candidates: list[str]) -> Optional[str]:
    """
    Match a Lichess display name to one of our canonical player names.
    Tries whole-name match first, then word-by-word on words longer than 3 chars.
    """
    lichess_lower = lichess_name.lower()
    # Exact match
    for player in candidates:
        if player.lower() == lichess_lower:
            return player
    # Word overlap (e.g. "Praggnanandhaa R" matches "Praggnanandhaa")
    for player in candidates:
        for word in player.lower().split():
            if len(word) > 3 and word in lichess_lower:
                return player
    return None


def match_game_to_db(lichess_white: str, lichess_black: str, section: str):
    """
    Return (white_canonical, black_canonical) matched to our player list,
    or (None, None) if either can't be matched.
    """
    players = OPEN_PLAYERS if section == "open" else WOMEN_PLAYERS
    white = _match_player(lichess_white, players)
    black = _match_player(lichess_black, players)
    return white, black
