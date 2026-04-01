# 2026 Chess Candidates Prediction Bot — Project Memory

## Project Overview
A Discord bot that lets server members predict game results for the 2026 FIDE Candidates Tournament. Users earn points for correct predictions. An admin enters official results which trigger automatic scoring.

## Tournament Facts
- **Event:** 2026 FIDE Candidates Tournament, Toronto, Canada
- **Open section:** April 3 – April 22, 2026 | 8 players | 14 rounds (double round-robin)
- **Women's section:** April 3 – April 20, 2026 | 8 players | 14 rounds
- **Rest days (both sections):** April 9, 13, 17
- **Round start time:** 14:00 UTC (10:00 AM EDT)
- **Prediction cutoff:** 30 minutes before each round (13:30 UTC)

## Tech Stack
- **Language:** Python 3.12+
- **Bot library:** discord.py 2.4+
- **Database:** SQLite 3 (via stdlib `sqlite3`)
- **Config:** python-dotenv
- **Commands:** Discord slash commands (app_commands)

## Architecture

```
candidates_prediction/
├── bot.py                  # Entry point; loads cogs, syncs slash commands
├── config.py               # Env var loading (BOT_TOKEN, GUILD_ID, etc.)
├── database.py             # All SQL — tables, queries, upserts
├── scoring.py              # Pure scoring logic (no DB I/O)
├── tournament_data.py      # Static data: players, pairings (Berger), dates
├── cogs/
│   ├── predictions.py      # /predict open|women, /mypredictions, /predictionstatus
│   ├── results.py          # /enterresult, /scoreround, /roundresults (admin)
│   ├── schedule.py         # /schedule, /nextround, /players, /about
│   └── leaderboard.py      # /leaderboard, /roundleaderboard, /mystats, /userstats
├── requirements.txt
├── .env.example
├── .gitignore
└── claude.md               # This file
```

## Database Schema
| Table         | Key columns                                                              |
|---------------|--------------------------------------------------------------------------|
| `users`       | user_id (PK), username, joined_at                                        |
| `games`       | game_id (PK), section, round_number, white_player, black_player, round_start_utc, cutoff_utc |
| `predictions` | prediction_id, user_id, game_id, prediction, submitted_at — UNIQUE(user_id, game_id) |
| `results`     | game_id (PK), result, entered_by, entered_at                             |
| `scores`      | score_id, user_id, game_id, prediction, actual, points — UNIQUE(user_id, game_id) |

## Scoring Rules
- Correct prediction: **+3 points**
- Correct decisive result (win/loss) bonus: **+1 point**
- Max per game: **4 points** (decisive) or **3 points** (draw)

## Slash Commands Reference

### Prediction commands (all users)
| Command | Description |
|---------|-------------|
| `/predict open [round]` | Predict Open section round (dropdowns per game) |
| `/predict women [round]` | Predict Women's section round |
| `/mypredictions [section]` | View your own predictions and outcomes |
| `/predictionstatus` | See submission counts per round |

### Result/admin commands
| Command | Description |
|---------|-------------|
| `/enterresult <game_id> <result>` | Enter official result; triggers scoring |
| `/scoreround open <round>` | Re-score all games in a round |
| `/scoreround women <round>` | Same for Women's |
| `/roundresults open [round]` | Show results + prediction distributions |
| `/roundresults women [round]` | Same for Women's |

### Schedule/info commands
| Command | Description |
|---------|-------------|
| `/schedule open [round]` | Full Open schedule or specific round |
| `/schedule women [round]` | Full Women's schedule or specific round |
| `/nextround` | When the next round starts (both sections) |
| `/players open` | List Open section players |
| `/players women` | List Women's section players |
| `/about` | Tournament overview and scoring rules |

### Leaderboard commands
| Command | Description |
|---------|-------------|
| `/leaderboard [section]` | Overall leaderboard |
| `/roundleaderboard open <round>` | Round-specific leaderboard |
| `/roundleaderboard women <round>` | Same for Women's |
| `/mystats [section]` | Your personal stats |
| `/userstats <user> [section]` | Another user's stats |

## Key Design Decisions
1. **Pairings generated at startup** via Berger round-robin algorithm — no hardcoded pairing list needed.
2. **Scores are materialised** in the `scores` table for fast leaderboard queries; they are rewritten if a result is updated.
3. **Predictions are ephemeral** (only the submitting user sees the prediction form) to keep channels clean.
4. **Auto-scorer background task** runs every 2 minutes to catch any predictions that weren't scored on result entry.
5. **Guild-scoped slash commands** register instantly during development; switch to global by clearing `DISCORD_GUILD_ID`.

## Setup Instructions
1. Create a bot at https://discord.com/developers/applications
2. Enable "applications.commands" and "bot" scopes; invite to your server
3. `pip install -r requirements.txt`
4. `cp .env.example .env` and fill in `DISCORD_BOT_TOKEN` and `DISCORD_GUILD_ID`
5. `python bot.py`

## Session Log
- **2026-04-01:** Initial implementation — full bot with predictions, results, scoring, schedule, and leaderboard.
