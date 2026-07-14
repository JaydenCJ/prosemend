"""The diff3 algorithm over arbitrary token sequences.

Classic hunk-based three-way merge, the same scheme git's xdl_merge uses:

1. diff base→ours and base→theirs independently (difflib.SequenceMatcher
   with ``autojunk`` disabled — the popularity heuristic misfires on prose,
   where common words repeat constantly);
2. cluster change hunks from the two sides whose base ranges overlap;
3. classify each cluster:

   - only one side changed             → take that side
   - both changed to the same thing    → take it (also covers both-deleted)
   - both changed differently          → conflict

Edits to *adjacent* tokens do not overlap and merge cleanly; two insertions
at the exact same point are ambiguous and conflict, matching diff3/git
semantics. The only difference from ``diff3``/``git merge-file`` is what a
token is: they hardcode lines, this module takes any hashable sequence, and
prosemend feeds it words.
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass
from typing import List, Sequence, Tuple, Union

__all__ = ["Resolved", "Conflicted", "merge_tokens"]


@dataclass(frozen=True)
class Resolved:
    """A run of tokens that merged cleanly."""

    tokens: Tuple[str, ...]


@dataclass(frozen=True)
class Conflicted:
    """A region where ours and theirs made different, overlapping changes."""

    base: Tuple[str, ...]
    ours: Tuple[str, ...]
    theirs: Tuple[str, ...]


Region = Union[Resolved, Conflicted]

# A change hunk: base[base_lo:base_hi] became side[side_lo:side_hi].
_Hunk = Tuple[int, int, int, int]


def _changes(base: Sequence[str], side: Sequence[str]) -> List[_Hunk]:
    matcher = difflib.SequenceMatcher(None, base, side, autojunk=False)
    return [
        (i1, i2, j1, j2)
        for tag, i1, i2, j1, j2 in matcher.get_opcodes()
        if tag != "equal"
    ]


def _joins(lo: int, hi: int, h_lo: int, h_hi: int) -> bool:
    """Does hunk [h_lo, h_hi) belong to the cluster spanning [lo, hi)?

    Zero-width ranges are insertion points: two insertions at the same point
    collide, an insertion strictly inside a changed range collides, but an
    insertion at the edge of a change does not (there is an unambiguous
    order: the insertion lands before or after the change).
    """
    if lo == hi and h_lo == h_hi:
        return lo == h_lo
    if h_lo == h_hi:
        return lo < h_lo < hi
    if lo == hi:
        return h_lo < lo < h_hi
    return h_lo < hi and lo < h_hi


def merge_tokens(
    base: Sequence[str], ours: Sequence[str], theirs: Sequence[str]
) -> List[Region]:
    """Three-way merge of token sequences into Resolved/Conflicted regions.

    Adjacent resolved runs are coalesced, so the result alternates between
    ``Resolved`` and ``Conflicted`` regions.
    """
    a = _changes(base, ours)
    b = _changes(base, theirs)
    regions: List[Region] = []

    def emit(tokens: Sequence[str]) -> None:
        if not tokens:
            return
        if regions and isinstance(regions[-1], Resolved):
            regions[-1] = Resolved(regions[-1].tokens + tuple(tokens))
        else:
            regions.append(Resolved(tuple(tokens)))

    pos = 0  # cursor along the base
    off_a = 0  # ours_index - base_index, valid at synced (unchanged) points
    off_b = 0
    ai = bi = 0
    while ai < len(a) or bi < len(b):
        # Seed a cluster with whichever pending hunk starts first in base.
        if bi >= len(b) or (ai < len(a) and a[ai][0] <= b[bi][0]):
            lo, hi = a[ai][0], a[ai][1]
        else:
            lo, hi = b[bi][0], b[bi][1]
        # Grow the cluster with every hunk (from either side) that overlaps.
        a_members: List[_Hunk] = []
        b_members: List[_Hunk] = []
        grown = True
        while grown:
            grown = False
            while ai < len(a) and _joins(lo, hi, a[ai][0], a[ai][1]):
                hi = max(hi, a[ai][1])
                a_members.append(a[ai])
                ai += 1
                grown = True
            while bi < len(b) and _joins(lo, hi, b[bi][0], b[bi][1]):
                hi = max(hi, b[bi][1])
                b_members.append(b[bi])
                bi += 1
                grown = True

        emit(base[pos:lo])  # stable text is identical in all three versions

        o_lo, t_lo = lo + off_a, lo + off_b
        off_a += sum((j2 - j1) - (i2 - i1) for i1, i2, j1, j2 in a_members)
        off_b += sum((j2 - j1) - (i2 - i1) for i1, i2, j1, j2 in b_members)
        o_hi, t_hi = hi + off_a, hi + off_b

        base_gap = tuple(base[lo:hi])
        ours_gap = tuple(ours[o_lo:o_hi])
        theirs_gap = tuple(theirs[t_lo:t_hi])
        if ours_gap == theirs_gap:
            emit(ours_gap)  # same change on both sides, or both deleted
        elif ours_gap == base_gap:
            emit(theirs_gap)  # only theirs changed
        elif theirs_gap == base_gap:
            emit(ours_gap)  # only ours changed
        else:
            regions.append(Conflicted(base_gap, ours_gap, theirs_gap))
        pos = hi

    emit(base[pos:])
    return regions
