# Contributing to prosemend

Thanks for your interest in contributing. Issues, discussions, and pull
requests are all welcome.

## Getting started

Python ≥3.9 and nothing else — the package has zero runtime dependencies.

```bash
git clone https://github.com/JaydenCJ/prosemend
cd prosemend
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
bash scripts/smoke.sh
```

`scripts/smoke.sh` merges the shipped example three ways, proves the
word-level pass eliminates the false conflict that line granularity
produces, and exercises driver mode, `--favor`, and `diff` end to end. It
must print `SMOKE OK`.

## Before you open a pull request

1. Format touched files consistently with the surrounding code (PEP 8,
   4-space indents; formatting is enforced in review).
2. Keep the tree warning-free: `python3 -W error -m pytest` must pass.
3. `pytest` — all tests must pass, fully offline.
4. `bash scripts/smoke.sh` — must print `SMOKE OK`.
5. Add tests for behavior changes; keep logic in pure, unit-testable
   modules (`tokens`, `blocks`, `sentences`, `diff3`, `render` take and
   return plain data).

## Ground rules

- **No new runtime dependencies.** `dependencies = []` is the flagship
  claim; test-only tooling belongs in the `dev` extra.
- **Never invent output.** Every byte of a merge result must come from one
  of the three inputs or a conflict-marker line — see
  [docs/merge-strategy.md](docs/merge-strategy.md) for the guarantees.
- **Round-tripping is sacred.** Segmentation, tokenization, and sentence
  splitting must reproduce their input byte-for-byte; add a round-trip
  assertion to any new tokenizer path.
- No network calls, no telemetry; the CLI only ever touches user-named
  files. Code comments and doc comments are written in English.
- Keep the three READMEs aligned: `README.md`, `README.zh.md`, and
  `README.ja.md` are line-for-line translations (English is authoritative).

## Reporting bugs

Please include `prosemend --version`, the three input files (or a minimal
trio that reproduces the shape of the problem), the exact command line, and
the output you expected. Merge bugs are almost always reproducible from a
trio of files, which makes them ideal test cases.

## Security

Please do not report security issues in public issues. Use GitHub's private
vulnerability reporting on this repository instead.
