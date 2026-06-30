# Football Predictor Case Study

## Goal

Build a coding-agent case study around a Python project that predicts a single match between two national football teams.

The expected user-facing output is probabilistic:

```text
Argentina vs France
Argentina win: 58%
Draw: 22%
France win: 20%
```

The objective is not to claim certainty about football results. The objective is to produce a reproducible prediction pipeline that the coding agent can inspect, run, evaluate, improve, and explain.

## Scope

In scope for the first version:

- Predict one match between two national teams.
- Use historical international match results.
- Compute Elo ratings from match history.
- Compute recent form from the last 5 matches.
- Compute goals for and against from the last 10 matches.
- Compute head-to-head signal from the last 8 direct matches.
- Use a Poisson goal model for win/draw/loss probabilities.
- Evaluate predictions with Brier score, log loss, and RPS.

Out of scope for the first version:

- Full World Cup simulation.
- Player market value scraping.
- Advanced injury or squad availability data.
- Live odds or betting-market integration.

## Data

Primary dataset target:

- `data/results.csv`
- Expected format compatible with international results datasets:
  - `date`
  - `home_team`
  - `away_team`
  - `home_score`
  - `away_score`
  - `tournament`
  - `city`
  - `country`
  - `neutral`

For development and tests, this repository includes `data/results_sample.csv`. The sample is only for smoke tests and does not represent an official historical dataset.

## Features

All features must be calculated using matches before the prediction date. This avoids data leakage.

| Feature | Meaning | Window |
| --- | --- | --- |
| Elo | General team strength | Full prior history |
| Recent form | Win/draw/loss momentum | Last 5 matches |
| Goals for | Attack proxy | Last 10 matches |
| Goals against | Defense proxy | Last 10 matches |
| Head-to-head | Direct matchup history | Last 8 direct matches |
| Home advantage | Host signal | Fixed adjustment |

## Models

### Baseline: Elo

The Elo difference between the teams is converted into win/draw/loss probabilities. This is the baseline that the main model should beat.

### Main model: Poisson

The Poisson model estimates expected goals for each team from:

- attack strength,
- opponent defensive weakness,
- Elo adjustment,
- home advantage.

The scoreline distribution is then summed to produce:

- team A win probability,
- draw probability,
- team B win probability.

## Evaluation

Evaluation is performed on historical matches using only previous data for every prediction.

Metrics:

- Brier score: lower is better.
- Log loss: lower is better.
- RPS: lower is better for ordered football outcomes.

## Agent responsibilities

The coding agent should be able to:

- Explore this project and explain its architecture.
- Run a prediction for a requested matchup.
- Evaluate the model on known historical matches.
- Detect possible data leakage.
- Use RAG and memory to explain decisions.
- Record relevant execution traces and task state.
