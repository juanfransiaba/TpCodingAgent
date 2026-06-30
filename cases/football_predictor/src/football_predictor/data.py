from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RESULTS_PATH = PROJECT_ROOT / "data" / "results.csv"
SAMPLE_RESULTS_PATH = PROJECT_ROOT / "data" / "results_sample.csv"

REQUIRED_COLUMNS = {
    "date",
    "home_team",
    "away_team",
    "home_score",
    "away_score",
    "tournament",
    "city",
    "country",
    "neutral",
}


def resolve_results_path(path: str | None = None) -> Path:
    if path:
        return Path(path)

    if DEFAULT_RESULTS_PATH.exists():
        return DEFAULT_RESULTS_PATH

    return SAMPLE_RESULTS_PATH


def load_results(path: str | None = None) -> pd.DataFrame:
    resolved_path = resolve_results_path(path)

    if not resolved_path.exists():
        raise FileNotFoundError(f"Results file not found: {resolved_path}")

    results = pd.read_csv(resolved_path)
    missing_columns = REQUIRED_COLUMNS - set(results.columns)

    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Missing required columns in {resolved_path}: {missing}")

    results = results.copy()
    results["date"] = pd.to_datetime(results["date"], errors="raise")
    results["home_score"] = pd.to_numeric(results["home_score"], errors="raise")
    results["away_score"] = pd.to_numeric(results["away_score"], errors="raise")
    results["neutral"] = results["neutral"].map(_parse_bool)

    return results.sort_values("date").reset_index(drop=True)


def matches_before(results: pd.DataFrame, match_date: str | None = None) -> pd.DataFrame:
    if match_date is None:
        return results.copy()

    cutoff = pd.to_datetime(match_date)
    return results[results["date"] < cutoff].copy()


def _parse_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value

    normalized = str(value).strip().lower()
    return normalized in {"true", "1", "yes", "y"}
