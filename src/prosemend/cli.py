"""The ``prosemend`` command-line interface.

Subcommands:

- ``merge OURS BASE THEIRS`` — diff3-compatible argument order; merged text
  goes to stdout (or ``-o``). Exit 0 = clean, 1 = conflicts, 2 = error.
- ``driver BASE OURS THEIRS`` — git merge-driver mode: same merge, but the
  result is written back over OURS in place, matching git's ``%O %A %B``
  placeholder order and exit-code contract.
- ``diff OLD NEW`` — word-level diff in wdiff notation. Exit 0 = identical,
  1 = differs, 2 = error.

All file IO is UTF-8. Only user-named files are ever read or written; the
tool makes no network calls and writes nothing outside ``-o``/OURS.
"""

from __future__ import annotations

import argparse
import sys
from typing import List, Optional

from . import __version__
from .merge import FAVOR_POLICIES, GRANULARITIES, STYLES, MergeOptions, merge_text
from .wdiff import word_diff

__all__ = ["main", "build_parser"]

EXIT_CLEAN = 0
EXIT_CONFLICTS = 1
EXIT_ERROR = 2


def _read(path: str) -> str:
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def _write(path: str, text: str) -> None:
    with open(path, "w", encoding="utf-8", newline="") as handle:
        handle.write(text)


def _count(n: int, noun: str) -> str:
    """``1 conflict`` / ``2 conflicts`` — summaries are read by humans."""
    return f"{n} {noun}" if n == 1 else f"{n} {noun}s"


def _add_merge_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--granularity",
        choices=GRANULARITIES,
        default="word",
        help="merge atom for prose: word (default), sentence, or line (plain diff3)",
    )
    parser.add_argument(
        "--favor",
        choices=FAVOR_POLICIES,
        default="none",
        help="auto-resolve remaining conflicts: ours, theirs, or union (default: none)",
    )
    parser.add_argument(
        "--style",
        choices=STYLES,
        default="git",
        help="conflict marker style; diff3 adds the ||||||| base section",
    )
    parser.add_argument(
        "--marker-size",
        type=int,
        default=7,
        metavar="N",
        help="length of conflict marker runs (git passes %%L here; default 7)",
    )


def _merge_options(args: argparse.Namespace, labels) -> MergeOptions:
    return MergeOptions(
        granularity=args.granularity,
        favor=args.favor,
        style=args.style,
        label_ours=labels[0],
        label_base=labels[1],
        label_theirs=labels[2],
        marker_size=args.marker_size,
    )


def _cmd_merge(args: argparse.Namespace) -> int:
    labels = list(args.label or [])
    if len(labels) > 3:
        print(
            "prosemend: error: at most three -L labels (ours, base, theirs)",
            file=sys.stderr,
        )
        return EXIT_ERROR
    defaults = [args.ours, args.base, args.theirs]
    labels += defaults[len(labels) :]
    ours = _read(args.ours)
    base = _read(args.base)
    theirs = _read(args.theirs)
    result = merge_text(base, ours, theirs, _merge_options(args, labels))
    if args.output:
        _write(args.output, result.text)
    else:
        sys.stdout.write(result.text)
    if not args.quiet:
        if result.auto_resolved:
            print(
                f"prosemend: auto-resolved {_count(result.auto_resolved, 'overlapping region')}",
                file=sys.stderr,
            )
        if result.conflicts:
            print(f"prosemend: {_count(result.conflicts, 'conflict')}", file=sys.stderr)
    return EXIT_CLEAN if result.clean else EXIT_CONFLICTS


def _cmd_driver(args: argparse.Namespace) -> int:
    name = args.path or args.ours
    labels = ["ours", "base", "theirs"]
    ours = _read(args.ours)
    base = _read(args.base)
    theirs = _read(args.theirs)
    result = merge_text(base, ours, theirs, _merge_options(args, labels))
    _write(args.ours, result.text)
    if result.conflicts and not args.quiet:
        print(f"prosemend: {name}: {_count(result.conflicts, 'conflict')}", file=sys.stderr)
    return EXIT_CLEAN if result.clean else EXIT_CONFLICTS


def _cmd_diff(args: argparse.Namespace) -> int:
    old = _read(args.old)
    new = _read(args.new)
    annotated, changed = word_diff(old, new, args.granularity)
    sys.stdout.write(annotated)
    if annotated and not annotated.endswith("\n"):
        sys.stdout.write("\n")
    return EXIT_CONFLICTS if changed else EXIT_CLEAN


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="prosemend",
        description="Word-level three-way merge for Markdown prose.",
    )
    parser.add_argument(
        "--version", action="version", version=f"prosemend {__version__}"
    )
    sub = parser.add_subparsers(dest="command", metavar="command")

    merge = sub.add_parser(
        "merge",
        help="three-way merge (diff3 argument order: OURS BASE THEIRS)",
        description="Merge OURS and THEIRS against BASE; result on stdout or -o.",
    )
    merge.add_argument("ours", help="our version (diff3: MINE)")
    merge.add_argument("base", help="common ancestor (diff3: OLDER)")
    merge.add_argument("theirs", help="their version (diff3: YOURS)")
    merge.add_argument("-o", "--output", metavar="FILE", help="write result to FILE")
    merge.add_argument(
        "-L",
        "--label",
        action="append",
        metavar="LABEL",
        help="conflict labels for ours/base/theirs; repeat up to three times",
    )
    merge.add_argument(
        "-q", "--quiet", action="store_true", help="suppress the stderr summary"
    )
    _add_merge_flags(merge)
    merge.set_defaults(func=_cmd_merge)

    driver = sub.add_parser(
        "driver",
        help="git merge-driver mode (%%O %%A %%B): writes the result over OURS",
        description="For .git/config: driver = prosemend driver %O %A %B",
    )
    driver.add_argument("base", help="ancestor version (git %%O)")
    driver.add_argument("ours", help="current version, rewritten in place (git %%A)")
    driver.add_argument("theirs", help="other branch's version (git %%B)")
    driver.add_argument(
        "--path", metavar="NAME", help="pathname for messages (git %%P)"
    )
    driver.add_argument(
        "-q", "--quiet", action="store_true", help="suppress the stderr summary"
    )
    _add_merge_flags(driver)
    driver.set_defaults(func=_cmd_driver)

    diff = sub.add_parser(
        "diff",
        help="word-level two-way diff in wdiff notation",
        description="Print NEW vs OLD with [-deletions-] and {+insertions+}.",
    )
    diff.add_argument("old", help="the old version")
    diff.add_argument("new", help="the new version")
    diff.add_argument(
        "--granularity",
        choices=GRANULARITIES,
        default="word",
        help="diff atom for prose (default: word)",
    )
    diff.set_defaults(func=_cmd_diff)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help(sys.stderr)
        return EXIT_ERROR
    try:
        return args.func(args)
    except OSError as exc:
        print(f"prosemend: error: {exc}", file=sys.stderr)
        return EXIT_ERROR
    except ValueError as exc:
        print(f"prosemend: error: {exc}", file=sys.stderr)
        return EXIT_ERROR


if __name__ == "__main__":
    sys.exit(main())
