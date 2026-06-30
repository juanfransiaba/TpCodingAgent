# Pandas Notes For Temporal Features

Use pandas to load tabular data, normalize dates, sort rows, and filter historical windows.

## Dates

Convert date columns once after reading the dataset:

```python
df["date"] = pd.to_datetime(df["date"], errors="raise")
```

For temporal features, always compare timestamps with a cutoff date:

```python
history = df[df["date"] < match_date]
```

This keeps only rows before the event being predicted.

## Sorting

Sort chronological data before rolling calculations:

```python
df = df.sort_values("date").reset_index(drop=True)
```

When calculating form or recent averages, sort first and then use `tail(window)`.

## Filtering Teams

For match data with home and away teams:

```python
team_matches = df[
    (df["home_team"] == team) | (df["away_team"] == team)
]
```

Use this filtered dataframe for recent form, goals for, and goals against.

## Groupby

Use `groupby` for aggregate summaries:

```python
summary = df.groupby("home_team")["home_score"].mean()
```

For temporal prediction, do the date filtering before groupby.
