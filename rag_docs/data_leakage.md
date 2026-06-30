# Data Leakage In Temporal Features

Data leakage happens when a model uses information that would not have been available at prediction time.

For match prediction, a feature for a match on `match_date` must only use matches before that date.

Correct pattern:

```python
history = df[df["date"] < match_date]
```

Do not use:

```python
history = df[df["date"] <= match_date]
```

The `<=` version can include the match being predicted if it has the same date.

## Rule

When predicting a match at a given date:

- use only rows where `date < match_date`;
- never use matches with equal or later dates;
- compute Elo, recent form, goals, and head-to-head from the filtered history;
- evaluate historical matches by walking forward through time.

If probabilities look unrealistically high, check for leakage before tuning the model.
