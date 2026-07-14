"""Block segmentation of Markdown documents.

The merge is Markdown-aware because tokenization depends on the *kind* of
block a line lives in. Code fences, tables, indented code, and YAML front
matter must never be merged word-by-word — reflowing a code line or a table
row corrupts it — so those blocks contribute whole lines as merge atoms, while
prose blocks (paragraphs, headings, lists, quotes) contribute word atoms.

Like the tokenizer, segmentation is lossless:
``"".join(b.text for b in segment(text)) == text`` for every input.

Deliberate simplifications for 0.1.0 (documented in the README):

- Indented code is only recognized at the document start or after a blank
  line; indented lines inside a paragraph are treated as prose continuations
  (which is what lazy list continuations look like).
- Tables are recognized by a leading pipe (``| ...``), the common GFM style.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List

__all__ = ["Block", "segment", "ATOMIC_KINDS"]

#: Block kinds whose lines are merge atoms (never merged word-by-word).
ATOMIC_KINDS = frozenset({"fence", "table", "front_matter", "indented_code"})

_FENCE_RE = re.compile(r"^( {0,3})(`{3,}|~{3,})(.*)$")
_TABLE_RE = re.compile(r"^ {0,3}\|")


@dataclass(frozen=True)
class Block:
    """A contiguous slice of the document with a single tokenization rule."""

    kind: str  # "prose" | "blank" | "fence" | "table" | "front_matter" | "indented_code"
    text: str


def _is_fence_open(line: str):
    """Return (char, min_len) when ``line`` opens a fence, else None.

    A backtick info string may not contain backticks (CommonMark), which is
    what distinguishes an opening fence from an inline code span at column 0.
    """
    m = _FENCE_RE.match(line.rstrip("\r\n"))
    if not m:
        return None
    marker, info = m.group(2), m.group(3)
    if marker[0] == "`" and "`" in info:
        return None
    return marker[0], len(marker)


def _is_fence_close(line: str, char: str, min_len: int) -> bool:
    stripped = line.rstrip("\r\n")
    if len(stripped) - len(stripped.lstrip(" ")) > 3:
        return False
    body = stripped.strip()
    return bool(body) and set(body) == {char} and len(body) >= min_len


def segment(text: str) -> List[Block]:
    """Split ``text`` into blocks; concatenating their texts restores it."""
    lines = text.splitlines(keepends=True)
    blocks: List[Block] = []
    n = len(lines)
    i = 0

    # YAML front matter: a '---' line at byte 0, closed by '---' or '...'.
    if n and lines[0].rstrip("\r\n") == "---":
        j = 1
        while j < n and lines[j].rstrip("\r\n") not in ("---", "..."):
            j += 1
        if j < n:
            blocks.append(Block("front_matter", "".join(lines[: j + 1])))
            i = j + 1

    while i < n:
        line = lines[i]

        fence = _is_fence_open(line)
        if fence is not None:
            char, min_len = fence
            j = i + 1
            while j < n:
                if _is_fence_close(lines[j], char, min_len):
                    j += 1
                    break
                j += 1
            # An unclosed fence swallows the rest of the file, exactly as a
            # Markdown renderer would display it.
            blocks.append(Block("fence", "".join(lines[i:j])))
            i = j
            continue

        if not line.strip():
            j = i
            while j < n and not lines[j].strip():
                j += 1
            blocks.append(Block("blank", "".join(lines[i:j])))
            i = j
            continue

        if _TABLE_RE.match(line):
            j = i
            while j < n and _TABLE_RE.match(lines[j]):
                j += 1
            blocks.append(Block("table", "".join(lines[i:j])))
            i = j
            continue

        if line.startswith(("    ", "\t")) and (
            not blocks or blocks[-1].kind in ("blank", "front_matter")
        ):
            j = i
            while j < n and lines[j].strip() and lines[j].startswith(("    ", "\t")):
                j += 1
            blocks.append(Block("indented_code", "".join(lines[i:j])))
            i = j
            continue

        # Prose: run until a blank line or the start of a special block.
        j = i + 1
        while j < n:
            nxt = lines[j]
            if not nxt.strip():
                break
            if _is_fence_open(nxt) is not None:
                break
            if _TABLE_RE.match(nxt):
                break
            j += 1
        blocks.append(Block("prose", "".join(lines[i:j])))
        i = j

    return blocks
