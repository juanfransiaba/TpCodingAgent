from dataclasses import dataclass

import pandas as pd

INITIAL_ELO = 1500.0
K_FACTOR = 30.0
HOME_ADVANTAGE = 60.0


@dataclass(frozen=True)
class EloSnapshot:
    ratings: dict[str, float]
    average_rating: float


def compute_elo(
    results: pd.DataFrame,
    initial_rating: float = INITIAL_ELO,
    k_factor: float = K_FACTOR,
    home_advantage: float = HOME_ADVANTAGE,
) -> EloSnapshot:
    ratings: dict[str, float] = {}

    for _, row in results.sort_values("date").iterrows():
        home_team = row["home_team"]
        away_team = row["away_team"]

        home_rating = ratings.get(home_team, initial_rating)
        away_rating = ratings.get(away_team, initial_rating)

        home_adjustment = 0.0 if bool(row["neutral"]) else home_advantage
        expected_home = expected_score(home_rating + home_adjustment, away_rating)
        actual_home = actual_score(row["home_score"], row["away_score"])

        change = k_factor * (actual_home - expected_home)
        ratings[home_team] = home_rating + change
        ratings[away_team] = away_rating - change

    average_rating = (
        sum(ratings.values()) / len(ratings)
        if ratings
        else initial_rating
    )

    return EloSnapshot(ratings=ratings, average_rating=average_rating)


def expected_score(team_rating: float, opponent_rating: float) -> float:
    return 1.0 / (1.0 + 10.0 ** ((opponent_rating - team_rating) / 400.0))


def actual_score(team_goals: int, opponent_goals: int) -> float:
    if team_goals > opponent_goals:
        return 1.0

    if team_goals == opponent_goals:
        return 0.5

    return 0.0
