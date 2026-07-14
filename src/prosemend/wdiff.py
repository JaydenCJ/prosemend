"""Two-way word-level diff in wdiff notation.

Powers ``prosemend diff``: deleted text is wrapped in ``[-…-]``, inserted
text in ``{+…+}``, and unchanged text is printed verbatim. Because it reuses
:func:`prosemend.merge.tokenize_document`, the diff has the same Markdown
awareness as the merge — code fences and tables diff line-by-line, prose
diffs word-by-word, links and code spans never get split.
"""

from __future__ import annotations

import difflib
from typing import Tuple

from .merge import tokenize_document

__all__ = ["word_diff"]


def word_diff(old: str, new: str, granularity: str = "word") -> Tuple[str, bool]:
    """Return (annotated_text, changed).

    ``changed`` is False when the two inputs are token-identical, so callers
    can map it straight onto a diff-style exit code.
    """
    a = tokenize_document(old, granularity)
    b = tokenize_document(new, granularity)
    matcher = difflib.SequenceMatcher(None, a, b, autojunk=False)
    parts = []
    changed = False
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            parts.append("".join(a[i1:i2]))
            continue
        changed = True
        deleted = "".join(a[i1:i2])
        inserted = "".join(b[j1:j2])
        if deleted:
            parts.append("[-" + deleted + "-]")
        if inserted:
            parts.append("{+" + inserted + "+}")
    return "".join(parts), changed
