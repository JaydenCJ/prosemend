"""Deterministic sentence splitting for prose blocks.

Used by the ``sentence`` merge granularity, where each sentence is one merge
atom: two edits inside the *same sentence* then conflict (stricter than word
granularity, looser than line granularity).

Rules, chosen to be predictable rather than clever:

- A sentence ends at ``. ! ? …`` (plus any closing quotes/brackets) followed
  by whitespace or end of text.
- Fullwidth CJK terminators ``。 ！ ？`` end a sentence with no space needed.
- Common abbreviations (``e.g.``, ``etc.``, ``Dr.``), single-letter initials
  (``J. Smith``), and decimal points (``3.14``) do not end a sentence.
- A bare number before the period at the start of a line is an ordered-list
  marker (``1. item``), not a sentence end.

Trailing whitespace is attached to the sentence it follows, so splitting is
lossless: ``"".join(split_sentences(text)) == text``.
"""

from __future__ import annotations

from typing import List

__all__ = ["split_sentences"]

_TERMINALS = ".!?…"
_CJK_TERMINALS = "。！？"
_CLOSERS = "\"')]}»”’」』"

_ABBREVIATIONS = frozenset(
    {
        "al", "approx", "ca", "cf", "dept", "dr", "e.g", "eq", "etc", "fig",
        "i.e", "jr", "mr", "mrs", "ms", "no", "p", "pp", "prof", "sr", "st",
        "vol", "vs",
    }
)


def _word_before(text: str, i: int) -> str:
    """The maximal run of word characters and dots ending just before ``i``."""
    j = i
    while j > 0 and (text[j - 1].isalnum() or text[j - 1] in "._"):
        j -= 1
    return text[j:i]


def _is_abbreviation(text: str, i: int, sentence_start: int) -> bool:
    """True when the ``.`` at index ``i`` does not terminate a sentence."""
    word = _word_before(text, i).strip(".")
    if not word:
        return False
    if word.lower() in _ABBREVIATIONS:
        return True
    if len(word) == 1 and word.isalpha() and word.isupper():
        return True  # initials: "J. Smith"
    if word.isdigit():
        # "1." at the start of a line/sentence is an ordered-list marker.
        head = text[sentence_start : i - len(word)]
        if not head.strip() or head.rstrip(" \t").endswith("\n"):
            return True
    return False


def split_sentences(text: str) -> List[str]:
    """Split prose into sentences; concatenating them restores ``text``."""
    out: List[str] = []
    n = len(text)
    start = 0
    i = 0
    while i < n:
        ch = text[i]
        if ch in _CJK_TERMINALS:
            j = i + 1
            while j < n and text[j] in _CJK_TERMINALS + _CLOSERS:
                j += 1
            while j < n and text[j].isspace():
                j += 1
            out.append(text[start:j])
            start = i = j
            continue
        if ch in _TERMINALS:
            if ch == "." and _is_abbreviation(text, i, start):
                i += 1
                continue
            j = i + 1
            while j < n and text[j] in _TERMINALS:
                j += 1  # "?!", "..."
            while j < n and text[j] in _CLOSERS:
                j += 1
            if j < n and not text[j].isspace():
                i = j  # "3.14", "v1.2.3": no boundary without trailing space
                continue
            while j < n and text[j].isspace():
                j += 1
            out.append(text[start:j])
            start = i = j
            continue
        i += 1
    if start < n:
        out.append(text[start:])
    return out
