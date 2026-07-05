import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from football_predictor.evaluate import evaluate_models


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate football prediction models.")
    parser.add_argument("--data", default=None)
    parser.add_argument("--min-history", type=int, default=10)
    parser.add_argument(
        "--max-eval",
        type=int,
        default=None,
        help="Score only the most recent N matches (held-out test set).",
    )

    args = parser.parse_args()

    results = evaluate_models(
        data_path=args.data,
        min_history_matches=args.min_history,
        max_eval_matches=args.max_eval,
    )

    for result in results:
        print(result.model_name)
        print(f"  matches_evaluated: {result.matches_evaluated}")
        print(f"  brier_score: {result.brier_score:.4f}")
        print(f"  log_loss: {result.log_loss:.4f}")
        print(f"  rps: {result.rps:.4f}")


if __name__ == "__main__":
    main()
