# Elo Rating Notes

Elo is a rating system that updates team strength after each match.

Each team starts with a default rating, often 1500.

## Expected Score

The expected score for team A is:

```python
expected_a = 1 / (1 + 10 ** ((rating_b - rating_a) / 400))
```

The expected score for team B is:

```python
expected_b = 1 - expected_a
```

## Actual Score

Use:

- win: `1.0`
- draw: `0.5`
- loss: `0.0`

## Update

After a match:

```python
new_rating_a = rating_a + k * (actual_a - expected_a)
new_rating_b = rating_b + k * (actual_b - expected_b)
```

Common `k` values are between 20 and 40.

For home advantage, add a temporary rating bonus to the home team when computing expected score. Do not permanently add home advantage to the rating.
