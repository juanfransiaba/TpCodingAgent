"""Mapa de calor de marcadores (Poisson) para un partido.

Usa la predicción real del proyecto (poisson_v2, goles esperados desde Elo) y la
misma funcion poisson_probability, asi la grilla refleja el modelo real, no datos mock.

Requiere matplotlib (no es dependencia del agente):
    pip install matplotlib

Uso:
    PYTHONPATH=cases/football_predictor/src \
    python cases/football_predictor/scripts/plot_scoreline_heatmap.py \
        --team-a England --team-b Mexico --out scoreline_heatmap.png
"""

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import matplotlib
matplotlib.use("Agg")  # solo guardar imagen, sin ventana
import matplotlib.pyplot as plt

from football_predictor.model import poisson_probability
from football_predictor.predict import predict_match


def scoreline_grid(expected_a: float, expected_b: float, max_goals: int) -> list[list[float]]:
    grid = []
    for goals_a in range(max_goals + 1):
        prob_a = poisson_probability(goals_a, expected_a)
        row = [prob_a * poisson_probability(goals_b, expected_b) for goals_b in range(max_goals + 1)]
        grid.append(row)
    return grid


def main() -> None:
    parser = argparse.ArgumentParser(description="Poisson scoreline heat map.")
    parser.add_argument("--team-a", required=True)
    parser.add_argument("--team-b", required=True)
    parser.add_argument("--date", default=None)
    parser.add_argument("--data", default=None)
    parser.add_argument("--host-team", default=None)
    parser.add_argument("--neutral", action="store_true", default=True)
    parser.add_argument("--not-neutral", dest="neutral", action="store_false")
    parser.add_argument("--max-goals", type=int, default=6)
    parser.add_argument("--out", default="scoreline_heatmap.png")
    args = parser.parse_args()

    prediction = predict_match(
        team_a=args.team_a,
        team_b=args.team_b,
        match_date=args.date,
        neutral=args.neutral,
        host_team=args.host_team,
        data_path=args.data,
    )

    max_goals = args.max_goals
    grid = scoreline_grid(prediction.expected_goals_a, prediction.expected_goals_b, max_goals)

    best_a, best_b, best_p = max(
        ((a, b, grid[a][b]) for a in range(max_goals + 1) for b in range(max_goals + 1)),
        key=lambda item: item[2],
    )

    fig, ax = plt.subplots(figsize=(7, 6))
    image = ax.imshow(grid, origin="lower", cmap="YlOrRd")

    ax.set_xlabel(f"Goles {prediction.team_b}")
    ax.set_ylabel(f"Goles {prediction.team_a}")
    ax.set_xticks(range(max_goals + 1))
    ax.set_yticks(range(max_goals + 1))

    for a in range(max_goals + 1):
        for b in range(max_goals + 1):
            ax.text(b, a, f"{grid[a][b] * 100:.1f}", ha="center", va="center", fontsize=7)

    ax.add_patch(
        plt.Rectangle((best_b - 0.5, best_a - 0.5), 1, 1, fill=False, edgecolor="blue", linewidth=2)
    )

    ax.set_title(
        f"{prediction.team_a} vs {prediction.team_b}  ({prediction.model_name})\n"
        f"{prediction.team_a} {prediction.team_a_win:.0%}  |  "
        f"Empate {prediction.draw:.0%}  |  "
        f"{prediction.team_b} {prediction.team_b_win:.0%}   —   "
        f"mas probable {prediction.team_a} {best_a}-{best_b} {prediction.team_b} ({best_p:.1%})",
        fontsize=9,
    )

    fig.colorbar(image, ax=ax, label="Probabilidad")
    fig.tight_layout()
    fig.savefig(args.out, dpi=150)
    print(f"Mapa de calor guardado en: {args.out}")


if __name__ == "__main__":
    main()