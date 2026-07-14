# How prosemend merges

This document specifies the merge pipeline, what a "merge atom" is for each
kind of Markdown content, and the guarantees the output carries. It is the
reference for anyone changing `tokens.py`, `blocks.py`, `diff3.py`, or
`render.py` — the four stages below map onto those four modules.

## 1. Block segmentation (`blocks.py`)

Each of the three input documents is split into blocks, losslessly
(concatenating block texts restores the input byte-for-byte):

| Block kind | Detected by | Merge atoms |
|---|---|---|
| `prose` | default (paragraphs, headings, lists, quotes) | words (see stage 2) |
| `fence` | ` ``` ` / `~~~` opener, matching closer | whole lines |
| `table` | lines starting with `\|` (≤3 leading spaces) | whole lines (rows) |
| `front_matter` | `---` at byte 0, closed by `---`/`...` | whole lines |
| `indented_code` | 4-space/tab indent after a blank line | whole lines |
| `blank` | whitespace-only lines | one atom per line |

Code, tables, and front matter are **never** merged word-by-word: reflowing
a code line or a table row corrupts it, so inside those blocks prosemend
behaves exactly like line-based diff3. Blank lines are individual atoms —
they are the sync anchors that stop unrelated paragraphs from entangling.

Known simplifications (deliberate for 0.1.0): indented code inside a list
item is treated as prose continuation, and only leading-pipe tables are
recognized. Both degrade to word-merging, never to data loss.

## 2. Prose tokenization (`tokens.py`)

Prose blocks become a flat token list — words, whitespace runs, punctuation
runs, and *atomic inline constructs* — with the same lossless property.
Atomicity decides what a merge can never split:

- words, including internal apostrophes/hyphens (`don't`, `well-known`);
- inline code spans (`` `git merge` ``), links, images, autolinks — a merge
  can replace a whole link but never leave half of one behind;
- runs of one punctuation character (`**`, `---`) so emphasis survives;
- CJK characters are one atom each, so Chinese/Japanese prose merges at
  character granularity with no word segmenter.

At `--granularity sentence`, prose becomes sentence atoms instead
(`sentences.py`), which makes any two edits inside one sentence a conflict.
At `--granularity line`, prose becomes line atoms — classic diff3, kept as
an escape hatch and a baseline for comparison.

## 3. Three-way merge (`diff3.py`)

The classic hunk-based diff3, generic over token sequences: diff base→ours
and base→theirs independently, cluster hunks whose base ranges overlap, then
classify each cluster — one side changed → take it; both made the identical
change → take it; both changed differently → conflict. Two insertions at the
same point conflict; edits to adjacent tokens do not. Alignment uses
`difflib.SequenceMatcher` with `autojunk=False` (the popularity heuristic
misclassifies common words as junk).

One post-pass: a conflict whose two sides are equal after collapsing
whitespace (one side reflowed a line, the other added a space) is
auto-resolved to ours and reported in the stderr summary, not as a conflict.

## 4. Conflict rendering (`render.py`)

The merge is word-level but conflict markers must be whole lines, or git,
editors, and `grep '<<<<<<<'` cannot parse the result. Each surviving
conflict is therefore widened to the enclosing line(s): the stable text
before and after it on the same line is duplicated into both variants, and
conflicts sharing a line coalesce into a single marker block. A conflict
that already sits on line boundaries is emitted as-is. `--style diff3` adds
the `|||||||` base section; marker length follows `--marker-size` (git's
`%L`).

## Guarantees

1. **Lossless plumbing** — segmentation, tokenization, and sentence
   splitting all round-trip byte-for-byte; a no-op merge returns the base
   unchanged.
2. **No invented text** — every byte of output comes from one of the three
   inputs (plus marker lines and, at most, one padding newline when a
   conflict ends the file without one).
3. **Conservative where it matters** — code, tables, and front matter merge
   line-wise; a genuine double edit of the same atom is always surfaced as
   a conflict unless a `--favor` policy was explicitly requested.
