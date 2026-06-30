from dataclasses import asdict

from football_predictor.data import load_results, matches_before, resolve_results_path
from football_predictor.features import build_match_features
from football_predictor.model import Prediction, predict_with_poisson


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


def format_prediction(prediction: Prediction, data_path: str | None = None) -> str:
    resolved_data_path = resolve_results_path(data_path)

    return "\n".join(
        [
            f"{prediction.team_a} vs {prediction.team_b}",
            f"{prediction.team_a} win: {prediction.team_a_win:.1%}",
            f"Draw: {prediction.draw:.1%}",
            f"{prediction.team_b} win: {prediction.team_b_win:.1%}",
            "",
            f"Model: {prediction.model_name}",
            f"Expected goals: {prediction.team_a} {prediction.expected_goals_a:.2f} - "
            f"{prediction.expected_goals_b:.2f} {prediction.team_b}",
            f"Data: {resolved_data_path}",
            "",
            "Explanation:",
            *[
                f"- {key}: {value}"
                for key, value in prediction.explanation.items()
            ],
        ]
    )
