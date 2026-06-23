# Contributing to Argus

## Development setup

```bash
git clone https://github.com/yourname/argus
cd argus
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[ml,api,dashboard,dev]"
```

## Running tests

```bash
# All tests with verbose output
pytest tests/ -v

# With coverage report
pytest tests/ --cov=argus --cov-report=html
open htmlcov/index.html
```

## Code style

Argus uses [ruff](https://docs.astral.sh/ruff/) for linting and formatting.

```bash
# Check for lint errors
ruff check argus/

# Auto-fix safe issues
ruff check argus/ --fix

# Format code
ruff format argus/
```

The CI pipeline runs `ruff check argus/` on every push. PRs that introduce lint
errors will not be merged.

## Adding a new collector

Collectors bridge real-world data sources into Argus `Event` objects.

1. Create `argus/collectors/your_collector.py`
2. Inherit from `BaseCollector` (`argus/collectors/base.py`)
3. Implement the two abstract methods:
   - `collect() -> list[Event]` — pull new events since the last call
   - `parse_line(raw: str) -> Event | None` — parse one raw line
4. Use `build_event()` from `argus/collectors/normalize.py` as the final step in `parse_line` to guarantee normalized field types
5. Guard any optional dependency imports inside method bodies (not at module level), matching the pattern in `NetworkCollector` (pyshark) and `FileCollector` (watchdog)
6. Add your collector to `argus/collectors/__init__.py`
7. Add an optional extras group to `pyproject.toml` if your collector requires a non-stdlib package
8. Write tests in `tests/test_phase7_collectors.py` using `tempfile.TemporaryDirectory()` for all I/O
9. Document in `docs/architecture.md` Module Reference table

## Adding a new detector

Detectors consume a feature vector (dict of floats) and return an anomaly score in [0, 1].

1. Add a new class in `argus/detectors.py` (or a separate file for large detectors)
2. Implement the same interface as `IsolationForestDetector`:
   - `train(feature_matrix: list[dict]) -> None`
   - `score(feature_vector: dict) -> float` — returns 0.0 if untrained, never raises
   - `save(path: str) -> None`
   - `load(path: str) -> None`
   - `is_trained: bool` property
3. Guard the heavy dependency import inside `train()`, not at module level
4. Pass your detector to `ArgusEngine(detector=YourDetector())`
5. Add tests to `tests/test_phase3_ml.py`

## Adding a new attack pattern

Correlation patterns live in `argus/correlator.py`.

1. Add an entry to the `PATTERNS` list with `name`, `description`, `condition` (human-readable), `bonus_points`, and `reason` (format string)
2. Add the evaluation logic to `evaluate_patterns()` — keep it a plain `if` block referencing the `window_stats` dict
3. If your pattern needs a new window statistic, add it to `compute_window_stats()`
4. Add a test to `tests/test_phase4_correlation.py`

## Pull request checklist

- [ ] All tests pass: `pytest tests/ -v`
- [ ] No lint errors: `ruff check argus/`
- [ ] Docstrings on all new public functions and classes
- [ ] `CHANGELOG.md` updated under a new `[Unreleased]` section
- [ ] Optional dependencies are import-guarded (not top-level)
- [ ] New collectors added to `argus/collectors/__init__.py`
- [ ] New optional extras added to `pyproject.toml`
