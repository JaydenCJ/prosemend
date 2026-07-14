"""Markdown-aware prose tokenizer.

Splits prose into merge atoms: words, whitespace runs, punctuation runs, and
atomic inline constructs (code spans, links, images, autolinks). Atoms are the
units the three-way merge aligns on, so the rules here decide what can and
cannot be torn apart by a merge:

- A word (including internal apostrophes and hyphens: ``don't``,
  ``well-known``) is one atom — a merge never splits a word.
- An inline code span, a link, or an image is one atom — a merge never leaves
  half a ``[text](url)`` behind.
- CJK characters are one atom each, so Chinese and Japanese prose merges at
  character granularity without needing a word segmenter.
- Runs of the same punctuation character (``**``, ``---``, ``>>``) stay
  together, so emphasis markers survive intact.

The load-bearing invariant is lossless round-tripping:
``"".join(tokenize_prose(text)) == text`` for every input. Tokens are plain
strings; the merge layer only needs equality, hashing, and concatenation.
"""

from __future__ import annotations

from typing import List

__all__ = ["tokenize_prose", "is_cjk"]

# Characters that glue a word run together when surrounded by word characters.
_WORD_JOINERS = "'’-"

_AUTOLINK_FORBIDDEN = set(" <>\n\t")


def is_cjk(ch: str) -> bool:
    """Return True for Han, Hiragana, and Katakana characters.

    These scripts have no inter-word spaces, so each character becomes its own
    merge atom (the same convention wdiff-CJK uses).
    """
    code = ord(ch)
    return (
        0x3040 <= code <= 0x30FF  # Hiragana + Katakana
        or 0x3400 <= code <= 0x4DBF  # CJK Extension A
        or 0x4E00 <= code <= 0x9FFF  # CJK Unified Ideographs
        or 0xF900 <= code <= 0xFAFF  # CJK Compatibility Ideographs
        or 0xFF66 <= code <= 0xFF9D  # Halfwidth Katakana
    )


def _scan_code_span(text: str, i: int) -> int:
    """Scan an inline code span opened by the backtick run at ``i``.

    Returns the exclusive end index, or -1 when the run is never closed by an
    equally long backtick run. Spans may cross a single newline (CommonMark
    allows soft-wrapped code spans) but never a blank line.
    """
    n = len(text)
    j = i
    while j < n and text[j] == "`":
        j += 1
    run = j - i
    k = j
    while k < n:
        ch = text[k]
        if ch == "`":
            m = k
            while m < n and text[m] == "`":
                m += 1
            if m - k == run:
                return m
            k = m
        elif ch == "\n":
            # A blank line ends the paragraph; the span cannot close.
            if k + 1 < n and text[k + 1] == "\n":
                return -1
            k += 1
        else:
            k += 1
    return -1


def _scan_link(text: str, i: int) -> int:
    """Scan ``[label](destination)`` starting at the ``[`` at index ``i``.

    Returns the exclusive end index, or -1 when the construct is malformed
    (unbalanced brackets, missing ``(...)``, or a blank line inside). One
    level of bracket nesting is supported, which covers images inside links.
    """
    n = len(text)
    depth = 0
    k = i
    while k < n:
        ch = text[k]
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                break
        elif ch == "\n":
            if k + 1 < n and text[k + 1] == "\n":
                return -1
        k += 1
    else:
        return -1
    # k is at the closing ']'; a destination must follow immediately.
    if k + 1 >= n or text[k + 1] != "(":
        return -1
    paren = 0
    m = k + 1
    while m < n:
        ch = text[m]
        if ch == "(":
            paren += 1
        elif ch == ")":
            paren -= 1
            if paren == 0:
                return m + 1
        elif ch == "\n":
            return -1
        m += 1
    return -1


def _scan_autolink(text: str, i: int) -> int:
    """Scan ``<scheme:...>`` or ``<user@host>`` starting at ``i``; -1 if not one."""
    n = len(text)
    k = i + 1
    saw_marker = False
    while k < n:
        ch = text[k]
        if ch == ">":
            return k + 1 if saw_marker and k > i + 1 else -1
        if ch in _AUTOLINK_FORBIDDEN:
            return -1
        if ch in ":@":
            saw_marker = True
        k += 1
    return -1


def tokenize_prose(text: str) -> List[str]:
    """Tokenize prose into merge atoms; concatenating them restores ``text``."""
    tokens: List[str] = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == "\n":
            tokens.append("\n")
            i += 1
            continue
        if ch.isspace():
            j = i
            while j < n and text[j].isspace() and text[j] != "\n":
                j += 1
            tokens.append(text[i:j])
            i = j
            continue
        if ch == "`":
            end = _scan_code_span(text, i)
            if end != -1:
                tokens.append(text[i:end])
                i = end
                continue
            j = i
            while j < n and text[j] == "`":
                j += 1
            tokens.append(text[i:j])  # unclosed backticks degrade to punctuation
            i = j
            continue
        if ch == "!" and i + 1 < n and text[i + 1] == "[":
            end = _scan_link(text, i + 1)
            if end != -1:
                tokens.append(text[i:end])
                i = end
                continue
        if ch == "[":
            end = _scan_link(text, i)
            if end != -1:
                tokens.append(text[i:end])
                i = end
                continue
        if ch == "<":
            end = _scan_autolink(text, i)
            if end != -1:
                tokens.append(text[i:end])
                i = end
                continue
        if is_cjk(ch):
            tokens.append(ch)
            i += 1
            continue
        if ch.isalnum() or ch == "_":
            j = i + 1
            while j < n:
                c = text[j]
                if is_cjk(c):
                    break
                if c.isalnum() or c == "_":
                    j += 1
                elif (
                    c in _WORD_JOINERS
                    and j + 1 < n
                    and (text[j + 1].isalnum() or text[j + 1] == "_")
                    and not is_cjk(text[j + 1])
                ):
                    j += 1
                else:
                    break
            tokens.append(text[i:j])
            i = j
            continue
        # Run of the identical punctuation character: '**', '---', '>>'.
        j = i
        while j < n and text[j] == ch:
            j += 1
        tokens.append(text[i:j])
        i = j
    return tokens
