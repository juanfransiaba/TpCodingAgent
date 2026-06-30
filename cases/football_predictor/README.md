# Football Predictor

Case-study project for the advanced coding agent.

This project predicts a single international football match between two national teams and returns probabilities for home/team A win, draw, and away/team B win.

## Quick Start

From the repository root:

```powershell
$env:PYTHONPATH="cases/football_predictor/src"
python cases/football_predictor/scripts/predict_match.py --team-a Argentina --team-b France
```

Evaluate the model on the available data:

```powershell
$env:PYTHONPATH="cases/football_predictor/src"
python cases/football_predictor/scripts/evaluate.py
```

## Data

The predictor looks for:

```text
cases/football_predictor/data/results.csv
```

If that file does not exist, it falls back to:

```text
cases/football_predictor/data/results_sample.csv
```

The sample file is only for smoke tests. A real run should use a complete historical international results dataset.
