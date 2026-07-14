"""prosemend — word-level three-way merge for Markdown prose.

Public API:

- :func:`merge_text` / :func:`merge_files` — three-way merge, returns a
  :class:`MergeResult` with the merged text and a conflict count.
- :func:`word_diff` — two-way word-level diff in wdiff notation.
- :class:`MergeOptions` — granularity, conflict style, labels, favor policy.

The package has zero runtime dependencies; everything runs on the Python
standard library.
"""

from __future__ import annotations

from .merge import MergeOptions, MergeResult, merge_files, merge_text, tokenize_document
from .wdiff import word_diff

__version__ = "0.1.0"

__all__ = [
    "MergeOptions",
    "MergeResult",
    "merge_files",
    "merge_text",
    "tokenize_document",
    "word_diff",
    "__version__",
]
