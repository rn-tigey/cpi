# Contributing to CPI

Thanks for your interest in improving Continuous Product Intelligence.

## Ground rule: the code stays product-agnostic

All product specificity lives in the PCM (`context/pcm.yaml` in a product's home,
seeded from the template in `cpi/templates/context/`) and in `config/sources.yaml`.
Pull requests that
hardcode a domain, market, or product into the Python code will be declined —
if the pipeline can't express something generically, improve the PCM schema or
the config surface instead.

## Dev setup

```bash
git clone https://github.com/rn-tigey/cpi.git && cd cpi
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## Running tests

Tests never call the network or the Anthropic API — `tests/conftest.py` forces
`CPI_DRY_RUN=1`, and network calls in scanner tests are mocked.

```bash
pytest
ruff check .
```

Both must pass before a PR. If you add behavior, add a test in the matching
suite (`tests/test_*.py`); keep tests keyless and offline.

## Pull requests

- Keep PRs focused — one behavior change per PR.
- Describe what changed and why; link an issue if one exists.
- Prompt changes (`prompts/*.md`) are code: explain the intended effect on
  triage/scoring behavior in the PR description.
- New signal scanners belong in `cpi/scanners/`, use the helpers in
  `base.py` (including `log_scan` for health reporting), and must be
  idempotent (safe to re-run; dedupe by URL).
