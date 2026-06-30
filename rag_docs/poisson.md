# Poisson Goal Model Notes

The Poisson distribution can model the number of goals scored by a football team.

If a team has expected goals `lambda_goals`, the probability of scoring `k` goals is:

```python
probability = exp(-lambda_goals) * lambda_goals**k / factorial(k)
```

## Scoreline Distribution

To estimate result probabilities:

1. Estimate expected goals for team A.
2. Estimate expected goals for team B.
3. Compute probabilities for goals from 0 to N for each team.
4. Multiply probabilities for every scoreline.
5. Sum scorelines:
   - A win when `goals_a > goals_b`
   - draw when `goals_a == goals_b`
   - B win when `goals_a < goals_b`

Example loop:

```python
for goals_a in range(max_goals + 1):
    for goals_b in range(max_goals + 1):
        probability = poisson_a[goals_a] * poisson_b[goals_b]
```

Poisson is useful because football has many low-scoring matches and draws.
