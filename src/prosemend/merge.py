"""High-level Markdown-aware three-way merge.

Pipeline:

1. :func:`tokenize_document` — segment each version into Markdown blocks
   (``blocks.segment``), then tokenize each block by kind: prose becomes
   word atoms (or sentence atoms at ``sentence`` granularity), while code
   fences, tables, indented code, and front matter become line atoms.
2. :func:`prosemend.diff3.merge_tokens` — the diff3 algorithm over that
   mixed-granularity token stream.
3. Auto-resolution — conflicts whose sides differ only in whitespace are
   resolved silently; a ``favor`` policy (ours/theirs/union) can resolve the
   rest, mirroring ``git merge-file --ours/--theirs/--union``.
4. :func:`prosemend.render.render` — widen surviving conflicts to line
   boundaries and draw git-style markers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Union

from .blocks import ATOMIC_KINDS, segment
from .diff3 import Conflicted, Resolved, merge_tokens
from .render import Conflict, MarkerStyle, render
from .sentences import split_sentences
from .tokens import tokenize_prose

__all__ = ["MergeOptions", "MergeResult", "merge_text", "merge_files", "tokenize_document"]

GRANULARITIES = ("word", "sentence", "line")
FAVOR_POLICIES = ("none", "ours", "theirs", "union")
STYLES = ("git", "diff3")


@dataclass(frozen=True)
class MergeOptions:
    """Knobs for :func:`merge_text`; the defaults match ``git merge-file``."""

    granularity: str = "word"  # word | sentence | line
    favor: str = "none"  # none | ours | theirs | union
    style: str = "git"  # git | diff3
    label_ours: str = "ours"
    label_base: str = "base"
    label_theirs: str = "theirs"
    marker_size: int = 7

    def __post_init__(self) -> None:
        if self.granularity not in GRANULARITIES:
            raise ValueError(f"granularity must be one of {GRANULARITIES}")
        if self.favor not in FAVOR_POLICIES:
            raise ValueError(f"favor must be one of {FAVOR_POLICIES}")
        if self.style not in STYLES:
            raise ValueError(f"style must be one of {STYLES}")
        if self.marker_size < 3:
            raise ValueError("marker_size must be at least 3")


@dataclass(frozen=True)
class MergeResult:
    """Outcome of a three-way merge."""

    text: str
    conflicts: int
    auto_resolved: int = 0
    labels: tuple = field(default=("ours", "base", "theirs"))

    @property
    def clean(self) -> bool:
        return self.conflicts == 0


def _split_lines(text: str) -> List[str]:
    return text.splitlines(keepends=True)


def tokenize_document(text: str, granularity: str = "word") -> List[str]:
    """Turn a Markdown document into a mixed-granularity token stream.

    Concatenating the tokens always restores ``text`` exactly.
    """
    if granularity not in GRANULARITIES:
        raise ValueError(f"granularity must be one of {GRANULARITIES}")
    tokens: List[str] = []
    for block in segment(text):
        if block.kind in ATOMIC_KINDS or granularity == "line":
            tokens.extend(_split_lines(block.text))
        elif block.kind == "blank":
            # Each blank line is its own atom: a strong sync anchor between
            # paragraphs that keeps unrelated paragraphs from entangling.
            tokens.extend(_split_lines(block.text))
        elif granularity == "sentence":
            tokens.extend(split_sentences(block.text))
        else:
            tokens.extend(tokenize_prose(block.text))
    return tokens


def _squash_ws(text: str) -> str:
    return " ".join(text.split())


def _auto_resolve(ours: str, theirs: str, favor: str) -> Optional[str]:
    """Resolve a conflict without markers, or return None to keep it."""
    if _squash_ws(ours) == _squash_ws(theirs):
        # Same words, different whitespace (reflowed line, double space):
        # not a real conflict. Ours wins arbitrarily but deterministically.
        return ours
    if favor == "ours":
        return ours
    if favor == "theirs":
        return theirs
    if favor == "union":
        joiner = "" if (ours.endswith(("\n", " ")) or not ours) else " "
        return ours + joiner + theirs
    return None


def merge_text(
    base: str, ours: str, theirs: str, options: Optional[MergeOptions] = None
) -> MergeResult:
    """Three-way merge ``ours`` and ``theirs`` against their common ``base``."""
    opts = options or MergeOptions()
    regions = merge_tokens(
        tokenize_document(base, opts.granularity),
        tokenize_document(ours, opts.granularity),
        tokenize_document(theirs, opts.granularity),
    )
    pieces: List[Union[str, Conflict]] = []
    auto_resolved = 0
    for region in regions:
        if isinstance(region, Resolved):
            pieces.append("".join(region.tokens))
            continue
        assert isinstance(region, Conflicted)
        ours_text = "".join(region.ours)
        base_text = "".join(region.base)
        theirs_text = "".join(region.theirs)
        resolved = _auto_resolve(ours_text, theirs_text, opts.favor)
        if resolved is not None:
            auto_resolved += 1
            pieces.append(resolved)
        else:
            pieces.append(Conflict(ours_text, base_text, theirs_text))
    style = MarkerStyle(
        style=opts.style,
        label_ours=opts.label_ours,
        label_base=opts.label_base,
        label_theirs=opts.label_theirs,
        marker_size=opts.marker_size,
    )
    text, conflict_blocks = render(pieces, style)
    return MergeResult(
        text=text,
        conflicts=conflict_blocks,
        auto_resolved=auto_resolved,
        labels=(opts.label_ours, opts.label_base, opts.label_theirs),
    )


def merge_files(
    ours_path: Union[str, Path],
    base_path: Union[str, Path],
    theirs_path: Union[str, Path],
    options: Optional[MergeOptions] = None,
) -> MergeResult:
    """Read three UTF-8 files (ours, base, theirs — diff3 order) and merge."""
    ours = Path(ours_path).read_text(encoding="utf-8")
    base = Path(base_path).read_text(encoding="utf-8")
    theirs = Path(theirs_path).read_text(encoding="utf-8")
    return merge_text(base, ours, theirs, options)
