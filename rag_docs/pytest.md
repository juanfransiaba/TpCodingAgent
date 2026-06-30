# Pytest Notes

Pytest is a simple framework for writing and running Python tests.

## Test Structure

Tests usually live in a `tests/` directory and files are named with the `test_*.py` pattern.

Example:

```python
def test_prediction_probabilities_sum_to_one():
    total = prediction.team_a_win + prediction.draw + prediction.team_b_win
    assert abs(total - 1.0) < 0.001
```

## Asserts

Use plain Python `assert` statements:

```python
assert result == expected
assert value > 0
assert "error" not in output.lower()
```

## Running Tests

Run all tests:

```bash
python -m pytest
```

Run one file:

```bash
python -m pytest tests/test_model.py
```

For a coding agent, only claim tests passed after the command actually ran successfully.
