# Changelog

All notable changes to this project are documented in this file. The format is
based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this
project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-07-13

### Added

- Word-level three-way merge engine for Markdown prose: hunk-based diff3
  over token sequences, so two edits to different words of the same line
  merge cleanly instead of producing a whole-line conflict.
- Markdown-aware tokenization: words (with internal apostrophes/hyphens),
  atomic inline code spans, links, images, and autolinks; CJK characters
  merge at character granularity. All tokenization round-trips
  byte-for-byte.
- Block segmentation that keeps code fences, pipe tables, indented code,
  and YAML front matter merging line-wise — code is never reflowed
  word-by-word.
- Three prose granularities: `word` (default), `sentence` (deterministic
  splitter with abbreviation, initial, decimal, and list-marker guards),
  and `line` (classic diff3 behavior, as an escape hatch and baseline).
- Line-scoped conflict rendering: word-level conflicts are widened to whole
  lines, conflicts sharing a line coalesce into one block, `git` and
  `diff3` marker styles, custom labels (`-L`), and `--marker-size` (git's
  `%L`).
- Auto-resolution of whitespace-only divergence (reflowed lines) and
  `--favor ours|theirs|union` policies mirroring `git merge-file`.
- `prosemend merge` (diff3 argument order, exit 0/1/2), `prosemend driver`
  (git merge-driver `%O %A %B` contract, rewrites `%A` in place), and
  `prosemend diff` (word-level wdiff notation).
- Python API: `merge_text`, `merge_files`, `word_diff`, `MergeOptions`,
  `MergeResult`.
- Runnable example trio in `examples/`, the merge-strategy design doc in
  `docs/`, 92 offline deterministic tests, and `scripts/smoke.sh`.

### Notes

- The repository ships no CI workflow; verification is local — `pip install -e '.[dev]' && pytest && bash scripts/smoke.sh`.

[0.1.0]: https://github.com/JaydenCJ/prosemend/releases/tag/v0.1.0
