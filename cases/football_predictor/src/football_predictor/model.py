import math
from dataclasses import dataclass

import pandas as pd

from football_predictor.features import MatchFeatures

MAX_GOALS = 10
MIN_EXPECTED_GOALS = 0.2
MAX_EXPECTED_GOALS = 4.5


@dataclass(frozen=True)
class Prediction:
    team_a: str
    team_b: str
    team_a_win: float
    draw: float
    team_b_win: float
    expected_goals_a: float
    expected_goals_b: float
    model_name: str
    explanation: dict[str, float | str | int | bool]


def predict_with_poisson(results: pd.DataFrame, features: MatchFeatures) -> Prediction:
    avg_goals = average_team_goals(results)

    attack_a = features.team_a.goals_for_avg / avg_goals
    attack_b = features.team_b.goals_for_avg / avg_goals
    defense_a = features.team_a.goals_against_avg / avg_goals
    defense_b = features.team_b.goals_against_avg / avg_goals

    elo_factor_a = elo_factor(features.team_a.elo, features.team_b.elo)
    elo_factor_b = elo_factor(features.team_b.elo, features.team_a.elo)

    form_factor_a = form_factor(
        features.team_a.recent_form_points,
        features.team_b.recent_form_points,
    )
    form_factor_b = form_factor(
        features.team_b.recent_form_points,
        features.team_a.recent_form_points,
    )

    h2h_factor_a = head_to_head_factor(features.head_to_head_a)
    h2h_factor_b = head_to_head_factor(1.0 - features.head_to_head_a)

    home_factor_a = home_factor(features.team_a.team, features)
    home_factor_b = home_factor(features.team_b.team, features)

    expected_a = clamp(
        avg_goals
        * attack_a
        * defense_b
        * elo_factor_a
        * form_factor_a
        * h2h_factor_a
        * home_factor_a
    )
    expected_b = clamp(
        avg_goals
        * attack_b
        * defense_a
        * elo_factor_b
        * form_factor_b
        * h2h_factor_b
        * home_factor_b
    )

    team_a_win, draw, team_b_win = poisson_outcome_probabilities(expected_a, expected_b)

    return Prediction(
        team_a=features.team_a.team,
        team_b=features.team_b.team,
        team_a_win=team_a_win,
        draw=draw,
        team_b_win=team_b_win,
        expected_goals_a=expected_a,
        expected_goals_b=expected_b,
        model_name="poisson_v1",
        explanation={
            "history_size": features.history_size,
            "team_a_elo": round(features.team_a.elo, 2),
            "team_b_elo": round(features.team_b.elo, 2),
            "team_a_recent_form_points": round(features.team_a.recent_form_points, 2),
            "team_b_recent_form_points": round(features.team_b.recent_form_points, 2),
            "team_a_goals_for_avg": round(features.team_a.goals_for_avg, 3),
            "team_b_goals_for_avg": round(features.team_b.goals_for_avg, 3),
            "team_a_goals_against_avg": round(features.team_a.goals_against_avg, 3),
            "team_b_goals_against_avg": round(features.team_b.goals_against_avg, 3),
            "head_to_head_a": round(features.head_to_head_a, 3),
            "team_a_form_factor": round(form_factor_a, 3),
            "team_b_form_factor": round(form_factor_b, 3),
            "team_a_h2h_factor": round(h2h_factor_a, 3),
            "team_b_h2h_factor": round(h2h_factor_b, 3),
            "neutral": features.neutral,
            "host_team": features.host_team or "",
        },
    )


def predict_with_elo(features: MatchFeatures) -> Prediction:
    diff = features.team_a.elo - features.team_b.elo
    expected_a = 1.0 / (1.0 + 10.0 ** (-diff / 400.0))

    draw = 0.26
    team_a_win = expected_a * (1.0 - draw)
    team_b_win = (1.0 - expected_a) * (1.0 - draw)

    return Prediction(
        team_a=features.team_a.team,
        team_b=features.team_b.team,
        team_a_win=team_a_win,
        draw=draw,
        team_b_win=team_b_win,
        expected_goals_a=0.0,
        expected_goals_b=0.0,
        model_name="elo_baseline",
        explanation={
            "team_a_elo": round(features.team_a.elo, 2),
            "team_b_elo": round(features.team_b.elo, 2),
            "elo_diff": round(diff, 2),
        },
    )


def poisson_outcome_probabilities(
    expected_goals_a: float,
    expected_goals_b: float,
    max_goals: int = MAX_GOALS,
) -> tuple[float, float, float]:
    team_a_win = 0.0
    draw = 0.0
    team_b_win = 0.0

    for goals_a in range(max_goals + 1):
        prob_a = poisson_probability(goals_a, expected_goals_a)

        for goals_b in range(max_goals + 1):
            probability = prob_a * poisson_probability(goals_b, expected_goals_b)

            if goals_a > goals_b:
                team_a_win += probability
            elif goals_a == goals_b:
                draw += probability
            else:
                team_b_win += probability

    total = team_a_win + draw + team_b_win
    return team_a_win / total, draw / total, team_b_win / total


def poisson_probability(goals: int, expected_goals: float) -> float:
    return (
        math.exp(-expected_goals)
        * expected_goals**goals
        / math.factorial(goals)
    )


def average_team_goals(results: pd.DataFrame) -> float:
    if results.empty:
        return 1.2

    goals = pd.concat([results["home_score"], results["away_score"]])
    return max(float(goals.mean()), 0.1)


def elo_factor(team_elo: float, opponent_elo: float) -> float:
    return clamp(1.0 + ((team_elo - opponent_elo) / 1000.0), 0.75, 1.25)


def form_factor(team_form: float, opponent_form: float) -> float:
    form_diff = (team_form - opponent_form) / 3.0
    return clamp(1.0 + (form_diff * 0.12), 0.9, 1.1)


def head_to_head_factor(team_h2h_score: float) -> float:
    return clamp(1.0 + ((team_h2h_score - 0.5) * 0.10), 0.95, 1.05)


def home_factor(team: str, features: MatchFeatures) -> float:
    if features.neutral or not features.host_team:
        return 1.0

    return 1.08 if team == features.host_team else 0.96


def clamp(value: float, minimum: float = MIN_EXPECTED_GOALS, maximum: float = MAX_EXPECTED_GOALS) -> float:
    return max(minimum, min(maximum, value))
