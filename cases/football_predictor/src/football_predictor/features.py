from dataclasses import dataclass

import pandas as pd

from football_predictor.elo import INITIAL_ELO, compute_elo

GOAL_CAP = 6


@dataclass(frozen=True)
class TeamFeatures:
    team: str
    elo: float
    recent_form_points: float
    goals_for_avg: float
    goals_against_avg: float
    matches_available: int


@dataclass(frozen=True)
class MatchFeatures:
    team_a: TeamFeatures
    team_b: TeamFeatures
    head_to_head_a: float
    neutral: bool
    host_team: str | None
    history_size: int


def build_match_features(
    results: pd.DataFrame,
    team_a: str,
    team_b: str,
    neutral: bool = True,
    host_team: str | None = None,
) -> MatchFeatures:
    elo_snapshot = compute_elo(results)

    return MatchFeatures(
        team_a=build_team_features(results, team_a, elo_snapshot.ratings),
        team_b=build_team_features(results, team_b, elo_snapshot.ratings),
        head_to_head_a=head_to_head_score(results, team_a, team_b),
        neutral=neutral,
        host_team=host_team,
        history_size=len(results),
    )


def build_team_features(
    results: pd.DataFrame,
    team: str,
    elo_ratings: dict[str, float],
) -> TeamFeatures:
    team_matches = get_team_matches(results, team)

    return TeamFeatures(
        team=team,
        elo=elo_ratings.get(team, INITIAL_ELO),
        recent_form_points=recent_form(team_matches, team),
        goals_for_avg=average_goals_for(team_matches, team),
        goals_against_avg=average_goals_against(team_matches, team),
        matches_available=len(team_matches),
    )


def get_team_matches(results: pd.DataFrame, team: str) -> pd.DataFrame:
    mask = (results["home_team"] == team) | (results["away_team"] == team)
    return results[mask].sort_values("date")


def recent_form(team_matches: pd.DataFrame, team: str, window: int = 5) -> float:
    recent = team_matches.tail(window)

    if recent.empty:
        return 1.0

    points = []

    for _, row in recent.iterrows():
        goals_for, goals_against = goals_for_against(row, team)

        if goals_for > goals_against:
            points.append(3)
        elif goals_for == goals_against:
            points.append(1)
        else:
            points.append(0)

    return sum(points) / len(points)


def average_goals_for(team_matches: pd.DataFrame, team: str, window: int = 10) -> float:
    recent = team_matches.tail(window)

    if recent.empty:
        return 1.2

    values = [goals_for_against(row, team)[0] for _, row in recent.iterrows()]
    return sum(values) / len(values)


def average_goals_against(team_matches: pd.DataFrame, team: str, window: int = 10) -> float:
    recent = team_matches.tail(window)

    if recent.empty:
        return 1.2

    values = [goals_for_against(row, team)[1] for _, row in recent.iterrows()]
    return sum(values) / len(values)


def goals_for_against(row: pd.Series, team: str) -> tuple[int, int]:
    if row["home_team"] == team:
        return cap_goals(row["home_score"]), cap_goals(row["away_score"])

    if row["away_team"] == team:
        return cap_goals(row["away_score"]), cap_goals(row["home_score"])

    raise ValueError(f"Team {team} is not part of this match")


def cap_goals(value: int | float) -> int:
    return min(int(value), GOAL_CAP)


def head_to_head_score(
    results: pd.DataFrame,
    team_a: str,
    team_b: str,
    window: int = 8,
) -> float:
    direct_matches = results[
        (
            (results["home_team"] == team_a)
            & (results["away_team"] == team_b)
        )
        | (
            (results["home_team"] == team_b)
            & (results["away_team"] == team_a)
        )
    ].sort_values("date").tail(window)

    if direct_matches.empty:
        return 0.5

    score = 0.0

    for _, row in direct_matches.iterrows():
        goals_a, goals_b = goals_for_against(row, team_a)

        if goals_a > goals_b:
            score += 1.0
        elif goals_a == goals_b:
            score += 0.5

    return score / len(direct_matches)
