import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from football_predictor.predict import format_prediction, predict_match


def main() -> None:
    parser = argparse.ArgumentParser(description="Predict a football match.")
    parser.add_argument("--team-a", required=True)
    parser.add_argument("--team-b", required=True)
    parser.add_argument("--date", default=None)
    parser.add_argument("--data", default=None)
    parser.add_argument("--host-team", default=None)
    parser.add_argument("--neutral", action="store_true", default=True)
    parser.add_argument("--not-neutral", dest="neutral", action="store_false")

    args = parser.parse_args()

    prediction = predict_match(
        team_a=args.team_a,
        team_b=args.team_b,
        match_date=args.date,
        neutral=args.neutral,
        host_team=args.host_team,
        data_path=args.data,
    )

    print(format_prediction(prediction, data_path=args.data))


if __name__ == "__main__":
    main()
