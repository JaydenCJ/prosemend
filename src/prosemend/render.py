"""Render merged pieces into text with line-scoped conflict markers.

The merge itself is word-level, but conflict markers must land on line
boundaries or no downstream tool (git, editors, `grep '<<<<<<<'`) can parse
the result. This module widens each conflict to the enclosing line(s):

- the stable text between the last newline and the conflict is *duplicated*
  into every variant (ours/base/theirs), and likewise the stable text from
  the conflict to the next newline;
- conflicts that share a line (no newline between them) coalesce into a
  single marker block, so a line never contains two half-open markers.

The variants inside a marker block therefore read as complete lines, exactly
like `git merge-file` output — only far fewer of them, because the word-level
pass already resolved every non-overlapping edit.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Tuple, Union

__all__ = ["Conflict", "render"]


@dataclass(frozen=True)
class Conflict:
    """An unresolved region, as flat text per side."""

    ours: str
    base: str
    theirs: str


Piece = Union[str, Conflict]


@dataclass(frozen=True)
class MarkerStyle:
    """How conflict blocks are drawn."""

    style: str = "git"  # "git" or "diff3" (diff3 adds the ||||||| base section)
    label_ours: str = "ours"
    label_base: str = "base"
    label_theirs: str = "theirs"
    marker_size: int = 7


def _line_aligned(*variants: str) -> bool:
    """True when every variant ends at a line boundary (or is empty)."""
    return all(not v or v.endswith("\n") for v in variants)


def _pull_prefix(out: List[str]) -> str:
    """Remove and return the text after the last newline already emitted."""
    prefix = ""
    while out:
        tail = out[-1]
        nl = tail.rfind("\n")
        if nl == -1:
            prefix = tail + prefix
            out.pop()
            continue
        prefix = tail[nl + 1 :] + prefix
        out[-1] = tail[: nl + 1]
        break
    return prefix


def _ensure_line(text: str) -> str:
    """Marker sections must be whole lines; pad a missing final newline."""
    if text and not text.endswith("\n"):
        return text + "\n"
    return text


def _marker_block(ours: str, base: str, theirs: str, style: MarkerStyle) -> str:
    m = style.marker_size
    parts = ["<" * m + " " + style.label_ours + "\n", _ensure_line(ours)]
    if style.style == "diff3":
        parts.append("|" * m + " " + style.label_base + "\n")
        parts.append(_ensure_line(base))
    parts.append("=" * m + "\n")
    parts.append(_ensure_line(theirs))
    parts.append(">" * m + " " + style.label_theirs + "\n")
    return "".join(parts)


def render(pieces: Iterable[Piece], style: MarkerStyle) -> Tuple[str, int]:
    """Assemble pieces into final text; returns (text, marker_block_count).

    The count is the number of marker blocks actually emitted, which can be
    lower than the number of ``Conflict`` pieces when several conflicts share
    a line and coalesce.
    """
    work: List[Piece] = list(pieces)
    out: List[str] = []
    blocks = 0
    i = 0
    n = len(work)
    while i < n:
        piece = work[i]
        if isinstance(piece, str):
            out.append(piece)
            i += 1
            continue
        prefix = _pull_prefix(out)
        ours = prefix + piece.ours
        base = prefix + piece.base
        theirs = prefix + piece.theirs
        i += 1
        # Absorb everything up to the next newline of stable text, merging
        # any further conflicts encountered on the same line. Stop as soon
        # as every variant sits on a line boundary — a conflict that is
        # already whole lines must not swallow the following line.
        while i < n:
            if _line_aligned(ours, base, theirs):
                break
            nxt = work[i]
            if isinstance(nxt, Conflict):
                ours += nxt.ours
                base += nxt.base
                theirs += nxt.theirs
                i += 1
                continue
            nl = nxt.find("\n")
            if nl == -1:
                ours += nxt
                base += nxt
                theirs += nxt
                i += 1
                continue
            shared = nxt[: nl + 1]
            ours += shared
            base += shared
            theirs += shared
            work[i] = nxt[nl + 1 :]
            break
        out.append(_marker_block(ours, base, theirs, style))
        blocks += 1
    return "".join(out), blocks
