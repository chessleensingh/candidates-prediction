"""
Scoring logic for predictions.

Scoring rules:
  - Correct result:          +3 points
  - Correct decisive result: +1 bonus point (only when the result is 1-0 or 0-1
                              and the prediction matches exactly)
  - Wrong prediction:         0 points
"""

from tournament_data import (
    RESULT_DRAW,
    POINTS_CORRECT,
    POINTS_DECISIVE_BONUS,
)


def calculate_points(prediction: str, actual: str) -> int:
    """
    Return the number of points earned for a single game prediction.

    Args:
        prediction: One of RESULT_WHITE_WIN, RESULT_DRAW, RESULT_BLACK_WIN.
        actual:     The real result with the same possible values.

    Returns:
        Integer score (0, 3, or 4).
    """
    if prediction != actual:
        return 0
    points = POINTS_CORRECT
    if actual != RESULT_DRAW:
        points += POINTS_DECISIVE_BONUS
    return points


def score_round(predictions: list[dict], actuals: list[dict]) -> list[dict]:
    """
    Score a full round.

    Args:
        predictions: List of dicts with keys 'game_id', 'user_id', 'prediction'.
        actuals:     List of dicts with keys 'game_id', 'result'.

    Returns:
        List of dicts with keys 'user_id', 'game_id', 'prediction',
        'actual', 'points'.
    """
    actual_by_game = {a["game_id"]: a["result"] for a in actuals}
    scored = []
    for pred in predictions:
        game_id = pred["game_id"]
        actual = actual_by_game.get(game_id)
        if actual is None:
            continue  # result not yet entered
        points = calculate_points(pred["prediction"], actual)
        scored.append(
            {
                "user_id": pred["user_id"],
                "game_id": game_id,
                "prediction": pred["prediction"],
                "actual": actual,
                "points": points,
            }
        )
    return scored
