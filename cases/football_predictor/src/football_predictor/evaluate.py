import math
from dataclasses import dataclass

import pandas as pd

from football_predictor.data import load_results
from football_predictor.features import build_match_features
from football_predictor.model import predict_with_elo, predict_with_poisson


@dataclass(frozen=True)
class EvaluationResult:
    model_name: str
    matches_evaluated: int
    brier_score: float
    log_loss: float
    rps: float


def evaluate_models(
    data_path: str | None = None,
    min_history_matches: int = 10,
    max_eval_matches: int | None = None,
) -> list[EvaluationResult]:
    results = load_results(data_path).sort_values("date").reset_index(drop=True)
    records: dict[str, list[tuple[list[float], list[int]]]] = {
        "elo_baseline": [],
        "poisson_v2": [],
    }

    # Optionally score only the most recent matches as a held-out test set.
    # Every prediction still uses the full history before that match, so there
    # is no data leakage; this only bounds the O(n^2) cost on large datasets.
    start_index = min_history_matches
    if max_eval_matches is not None:
        start_index = max(min_history_matches, len(results) - max_eval_matches)

    for index, row in results.iterrows():
        if index < start_index:
            continue

        history = results.iloc[:index].copy()
        features = build_match_features(
            history,
            team_a=row["home_team"],
            team_b=row["away_team"],
            neutral=bool(row["neutral"]),
            host_team=None if bool(row["neutral"]) else row["home_team"],
        )

        actual = actual_vector(int(row["home_score"]), int(row["away_score"]))
        elo_prediction = predict_with_elo(features)
        poisson_prediction = predict_with_poisson(history, features)

        records["elo_baseline"].append((prediction_vector(elo_prediction), actual))
        records["poisson_v2"].append((prediction_vector(poisson_prediction), actual))

    return [
        build_evaluation_result(model_name, pairs)
        for model_name, pairs in records.items()
    ]


def actual_vector(team_a_goals: int, team_b_goals: int) -> list[int]:
    if team_a_goals > team_b_goals:
        return [1, 0, 0]

    if team_a_goals == team_b_goals:
        return [0, 1, 0]

    return [0, 0, 1]


def prediction_vector(prediction) -> list[float]:
    return [prediction.team_a_win, prediction.draw, prediction.team_b_win]


def build_evaluation_result(
    model_name: str,
    pairs: list[tuple[list[float], list[int]]],
) -> EvaluationResult:
    if not pairs:
        return EvaluationResult(
            model_name=model_name,
            matches_evaluated=0,
            brier_score=0.0,
            log_loss=0.0,
            rps=0.0,
        )

    return EvaluationResult(
        model_name=model_name,
        matches_evaluated=len(pairs),
        brier_score=sum(brier_score(pred, actual) for pred, actual in pairs) / len(pairs),
        log_loss=sum(log_loss(pred, actual) for pred, actual in pairs) / len(pairs),
        rps=sum(rps(pred, actual) for pred, actual in pairs) / len(pairs),
    )


def brier_score(predicted: list[float], actual: list[int]) -> float:
    return sum((probability - outcome) ** 2 for probability, outcome in zip(predicted, actual))


def log_loss(predicted: list[float], actual: list[int]) -> float:
    epsilon = 1e-12
    return -sum(
        outcome * math.log(max(epsilon, min(1.0 - epsilon, probability)))
        for probability, outcome in zip(predicted, actual)
    )


def rps(predicted: list[float], actual: list[int]) -> float:
    predicted_series = pd.Series(predicted).cumsum()
    actual_series = pd.Series(actual).cumsum()
    return float(((predicted_series - actual_series) ** 2).sum() / (len(predicted) - 1))
