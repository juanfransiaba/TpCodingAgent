import math
from dataclasses import dataclass

import pandas as pd

from football_predictor.features import MatchFeatures

MAX_GOALS = 10
MIN_EXPECTED_GOALS = 0.2
MAX_EXPECTED_GOALS = 4.5

# poisson_v2: expected goals driven by Elo supremacy (log-linear) instead of a
# stack of clamped heuristic factors. Parameters were selected on a validation
# window (matches [-1300:-300]) and confirmed on an untouched test set (last 300):
# it beats the Elo baseline on Brier, log loss and RPS, while poisson_v1 did not.
ELO_GOAL_SENSITIVITY = 0.9   # gamma: how strongly Elo difference shifts goal supremacy
HOME_ELO_BONUS = 60.0        # Elo points added to the host team (matches elo.HOME_ADVANTAGE)
RECENT_GOALS_WEIGHT = 0.5    # how much recent goal volume scales the total (0 = pure Elo)


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

    # Goal supremacy comes from the Elo difference (plus a host bonus), mapped
    # log-linearly onto each team's expected goals. This uses Elo -- the single
    # best-calibrated signal -- directly, instead of diluting it into a small
    # clamped factor as poisson_v1 did.
    elo_gap = features.team_a.elo - features.team_b.elo + home_elo_bonus(features)
    supremacy = math.exp(ELO_GOAL_SENSITIVITY * (elo_gap / 400.0))

    # Recent goal volume of both teams scales the total number of goals, at a
    # moderate weight so noisy short-term form does not dominate.
    recent_goal_level = average_recent_goal_level(features) / avg_goals
    total_factor = recent_goal_level**RECENT_GOALS_WEIGHT

    expected_a = clamp(avg_goals * total_factor * supremacy)
    expected_b = clamp(avg_goals * total_factor / supremacy)

    team_a_win, draw, team_b_win = poisson_outcome_probabilities(expected_a, expected_b)

    return Prediction(
        team_a=features.team_a.team,
        team_b=features.team_b.team,
        team_a_win=team_a_win,
        draw=draw,
        team_b_win=team_b_win,
        expected_goals_a=expected_a,
        expected_goals_b=expected_b,
        model_name="poisson_v2",
        explanation={
            "history_size": features.history_size,
            "team_a_elo": round(features.team_a.elo, 2),
            "team_b_elo": round(features.team_b.elo, 2),
            "elo_gap_with_home": round(elo_gap, 2),
            "elo_goal_sensitivity": ELO_GOAL_SENSITIVITY,
            "team_a_goals_for_avg": round(features.team_a.goals_for_avg, 3),
            "team_b_goals_for_avg": round(features.team_b.goals_for_avg, 3),
            "team_a_goals_against_avg": round(features.team_a.goals_against_avg, 3),
            "team_b_goals_against_avg": round(features.team_b.goals_against_avg, 3),
            "head_to_head_a": round(features.head_to_head_a, 3),
            "neutral": features.neutral,
            "host_team": features.host_team or "",
        },
    )


def home_elo_bonus(features: MatchFeatures) -> float:
    """Elo bonus for the host team, signed toward team_a. Zero on neutral ground."""

    if features.neutral or not features.host_team:
        return 0.0

    if features.host_team == features.team_a.team:
        return HOME_ELO_BONUS

    if features.host_team == features.team_b.team:
        return -HOME_ELO_BONUS

    return 0.0


def average_recent_goal_level(features: MatchFeatures) -> float:
    """Average of both teams' recent goals scored and conceded."""

    return (
        features.team_a.goals_for_avg
        + features.team_a.goals_against_avg
        + features.team_b.goals_for_avg
        + features.team_b.goals_against_avg
    ) / 4.0


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


def clamp(value: float, minimum: float = MIN_EXPECTED_GOALS, maximum: float = MAX_EXPECTED_GOALS) -> float:
    return max(minimum, min(maximum, value))
