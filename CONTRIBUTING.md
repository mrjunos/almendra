# Contributing to almendra

Thanks for your interest. almendra is an open investigation as much as a codebase
— contributions to data, taxonomy review, and capture/hardware design are as
valued as code.

## Development setup

Requires [`uv`](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/mrjunos/almendra.git
cd almendra
uv sync --extra dev      # fast, torch-free — lint, test, `almendra info`
# or: make setup         # everything (torch, onnx, dvc) for pipeline work
```

## Everyday commands

| Command | Does |
|---------|------|
| `make test` | Run the test suite |
| `make lint` | Ruff lint + format check |
| `make format` | Auto-format and apply safe fixes |
| `make info` | Print the taxonomy and project status |

CI runs `make lint` and `make test` on every push and PR — run them locally first.

## Code style
- Formatted and linted with **ruff** (config in `pyproject.toml`).
- Python ≥ 3.11; prefer type hints and short, documented functions.
- Keep core (`almendra` import) **torch-free**; heavy deps stay in extras.

## Tests
- `pytest`, tests in `tests/`.
- New behaviour needs a test. Bug fixes should add a regression test.

## Commits & PRs
- Small, focused commits with imperative messages (`Add fusion head`).
- Open a PR against `main`; describe *what* and *why*. CI must be green.

## Extending the project

**Add a public dataset** — create `data/sources/<name>.yaml` (copy an existing
adapter), provide the `class_map` to canonical taxonomy classes, and add a
datasheet under `docs/datasheets/`. Never commit dataset payloads.

**Add a model backbone** — register it in `src/almendra/models/backbone.py` and
add a `configs/model/<name>.yaml`. No training-code change should be needed.

**Change the taxonomy** — `data/taxonomy.yaml` is the single source of truth.
Any change bumps `schema_version` and needs an ADR (see below).

## Architecture decisions
Significant decisions are recorded as ADRs in `docs/adr/`. To propose one, copy
the format of an existing ADR and open it in a PR.

## Licence
By contributing you agree your contributions are licensed under [Apache-2.0](LICENSE).
