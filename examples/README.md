# prosemend examples

Three versions of the same document, edited concurrently the way two people
on a shared Syncthing folder (or two git branches) actually edit prose:

| File | Role | Edits relative to `base.md` |
|---|---|---|
| `base.md` | common ancestor | — |
| `ours.md` | our copy | front-matter `status`, one word in the paragraph (`drafts` → `outlines`), the table's `owner` column |
| `theirs.md` | their copy | a different word in the *same* paragraph line (`vague` → `half-baked`), both code-fence lines (`v1.2.0` → `v1.3.0`) |

Merge them word-level — clean, all four edits survive:

```bash
prosemend merge examples/ours.md examples/base.md examples/theirs.md
```

Now replay the exact merge diff3 and git would do, by dropping to line
granularity — the paragraph both sides touched becomes a conflict:

```bash
prosemend merge --granularity line \
  examples/ours.md examples/base.md examples/theirs.md
```

That one false conflict is the difference this tool exists for. The code
fence and the table still merged line-wise in both runs: prosemend never
merges code or table rows word-by-word.

See what changed between any two versions in wdiff notation:

```bash
prosemend diff examples/base.md examples/theirs.md
```

`scripts/smoke.sh` runs all of the above end-to-end and asserts on the
output; it prints `SMOKE OK` when everything holds.
