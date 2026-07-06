from dataclasses import asdict

from football_predictor.data import load_results, matches_before, resolve_results_path
from football_predictor.features import build_match_features
from football_predictor.model import (
    MAX_GOALS,
    Prediction,
    poisson_probability,
    predict_with_poisson,
)


def predict_match(
        team_a: str,
        team_b: str,
        match_date: str | None = None,
        neutral: bool = True,
        host_team: str | None = None,
        data_path: str | None = None,
) -> Prediction:
    results = load_results(data_path)
    history = matches_before(results, match_date)

    features = build_match_features(
        history,
        team_a=team_a,
        team_b=team_b,
        neutral=neutral,
        host_team=host_team,
    )

    return predict_with_poisson(history, features)


def prediction_to_dict(prediction: Prediction) -> dict:
    return asdict(prediction)


def top_scorelines(
        expected_goals_a: float,
        expected_goals_b: float,
        top_n: int = 6,
        max_goals: int = MAX_GOALS,
) -> list[tuple[int, int, float]]:
    """Most likely exact scorelines from the Poisson goal distribution."""

    scorelines: list[tuple[int, int, float]] = []

    for goals_a in range(max_goals + 1):
        prob_a = poisson_probability(goals_a, expected_goals_a)

        for goals_b in range(max_goals + 1):
            probability = prob_a * poisson_probability(goals_b, expected_goals_b)
            scorelines.append((goals_a, goals_b, probability))

    scorelines.sort(key=lambda item: item[2], reverse=True)
    return scorelines[:top_n]


def format_prediction(prediction: Prediction, data_path: str | None = None) -> str:
    resolved_data_path = resolve_results_path(data_path)

    lines = [
        f"{prediction.team_a} vs {prediction.team_b}",
        f"{prediction.team_a} win: {prediction.team_a_win:.1%}",
        f"Draw: {prediction.draw:.1%}",
        f"{prediction.team_b} win: {prediction.team_b_win:.1%}",
        "",
        f"Model: {prediction.model_name}",
        f"Expected goals: {prediction.team_a} {prediction.expected_goals_a:.2f} - "
        f"{prediction.expected_goals_b:.2f} {prediction.team_b}",
        f"Data: {resolved_data_path}",
    ]

    # Only meaningful for goal-based models (Elo baseline has no expected goals).
    if prediction.expected_goals_a > 0 and prediction.expected_goals_b > 0:
        lines.append("")
        lines.append("Most likely scorelines:")
        lines.extend(
            f"- {prediction.team_a} {goals_a}-{goals_b} {prediction.team_b}: {probability:.1%}"
            for goals_a, goals_b, probability in top_scorelines(
                prediction.expected_goals_a,
                prediction.expected_goals_b,
            )
        )

    lines.extend(
        [
            "",
            "Explanation:",
            *[f"- {key}: {value}" for key, value in prediction.explanation.items()],
        ]
    )

    return "\n".join(lines)