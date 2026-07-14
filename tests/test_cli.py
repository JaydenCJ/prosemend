"""CLI behavior: subcommands, exit codes, file IO, and the driver contract."""

import pytest

from prosemend import __version__
from prosemend.cli import main

BASE = "The quick brown fox jumps over the lazy dog.\n"
OURS = "The swift brown fox jumps over the lazy dog.\n"
THEIRS = "The quick brown fox leaps over the lazy dog.\n"
THEIRS_CLASH = "The speedy brown fox jumps over the lazy dog.\n"


@pytest.fixture
def files(tmp_path):
    def write(name, text):
        path = tmp_path / name
        path.write_text(text, encoding="utf-8")
        return str(path)

    return tmp_path, write


def test_merge_clean_exits_zero_and_prints_result(files, capsys):
    tmp, write = files
    rc = main(["merge", write("o.md", OURS), write("b.md", BASE), write("t.md", THEIRS)])
    out = capsys.readouterr().out
    assert rc == 0
    assert out == "The swift brown fox leaps over the lazy dog.\n"


def test_merge_conflict_exits_one_and_reports_on_stderr(files, capsys):
    tmp, write = files
    rc = main(
        ["merge", write("o.md", OURS), write("b.md", BASE), write("t.md", THEIRS_CLASH)]
    )
    captured = capsys.readouterr()
    assert rc == 1
    assert "<<<<<<<" in captured.out
    assert captured.err == "prosemend: 1 conflict\n"


def test_merge_two_conflicts_pluralize_the_stderr_summary(files, capsys):
    tmp, write = files
    base = "Alpha one.\n\nBeta two.\n"
    ours = "Alpha ONE.\n\nBeta TWO.\n"
    theirs = "Alpha uno.\n\nBeta dos.\n"
    rc = main(["merge", write("o.md", ours), write("b.md", base), write("t.md", theirs)])
    assert rc == 1
    assert capsys.readouterr().err == "prosemend: 2 conflicts\n"


def test_merge_more_than_three_labels_is_a_usage_error(files, capsys):
    tmp, write = files
    rc = main(
        ["merge", "-L", "a", "-L", "b", "-L", "c", "-L", "d",
         write("o.md", OURS), write("b.md", BASE), write("t.md", THEIRS)]
    )
    # Exit 2, not 1: a caller (git) must never mistake a usage error for
    # "merged with conflicts".
    assert rc == 2
    assert "at most three -L labels" in capsys.readouterr().err


def test_merge_quiet_suppresses_stderr_summary(files, capsys):
    tmp, write = files
    rc = main(
        ["merge", "-q", write("o.md", OURS), write("b.md", BASE), write("t.md", THEIRS_CLASH)]
    )
    assert rc == 1
    assert capsys.readouterr().err == ""


def test_merge_output_flag_writes_file_not_stdout(files, capsys):
    tmp, write = files
    out_path = tmp / "merged.md"
    rc = main(
        ["merge", "-o", str(out_path),
         write("o.md", OURS), write("b.md", BASE), write("t.md", THEIRS)]
    )
    assert rc == 0
    assert capsys.readouterr().out == ""
    assert out_path.read_text(encoding="utf-8") == (
        "The swift brown fox leaps over the lazy dog.\n"
    )


def test_merge_labels_flow_into_markers(files, capsys):
    tmp, write = files
    rc = main(
        ["merge", "-L", "mine.md", "-L", "old.md", "-L", "yours.md", "--style", "diff3",
         write("o.md", OURS), write("b.md", BASE), write("t.md", THEIRS_CLASH)]
    )
    out = capsys.readouterr().out
    assert rc == 1
    assert "<<<<<<< mine.md\n" in out
    assert "||||||| old.md\n" in out
    assert ">>>>>>> yours.md\n" in out


def test_merge_default_labels_are_the_file_paths(files, capsys):
    tmp, write = files
    ours_path = write("o.md", OURS)
    theirs_path = write("t.md", THEIRS_CLASH)
    main(["merge", ours_path, write("b.md", BASE), theirs_path])
    out = capsys.readouterr().out
    assert f"<<<<<<< {ours_path}\n" in out
    assert f">>>>>>> {theirs_path}\n" in out


def test_merge_favor_union_exits_zero(files, capsys):
    tmp, write = files
    rc = main(
        ["merge", "--favor", "union",
         write("o.md", OURS), write("b.md", BASE), write("t.md", THEIRS_CLASH)]
    )
    assert rc == 0
    assert "<<<<<<<" not in capsys.readouterr().out


def test_driver_rewrites_ours_in_place_git_argument_order(files):
    tmp, write = files
    base_path = write("O", BASE)  # git %O
    ours_path = write("A", OURS)  # git %A
    theirs_path = write("B", THEIRS)  # git %B
    rc = main(["driver", base_path, ours_path, theirs_path])
    assert rc == 0
    merged = (tmp / "A").read_text(encoding="utf-8")
    assert merged == "The swift brown fox leaps over the lazy dog.\n"


def test_driver_conflict_writes_markers_and_exits_one(files, capsys):
    tmp, write = files
    rc = main(
        ["driver", "--path", "notes.md",
         write("O", BASE), write("A", OURS), write("B", THEIRS_CLASH)]
    )
    assert rc == 1
    assert capsys.readouterr().err == "prosemend: notes.md: 1 conflict\n"
    assert "<<<<<<< ours" in (tmp / "A").read_text(encoding="utf-8")


def test_driver_marker_size_matches_gits_percent_l(files):
    tmp, write = files
    rc = main(
        ["driver", "--marker-size", "15",
         write("O", BASE), write("A", OURS), write("B", THEIRS_CLASH)]
    )
    assert rc == 1
    merged = (tmp / "A").read_text(encoding="utf-8")
    assert "<" * 15 + " ours\n" in merged
    assert "<" * 16 not in merged


def test_diff_identical_files_exits_zero(files, capsys):
    tmp, write = files
    rc = main(["diff", write("a.md", BASE), write("b.md", BASE)])
    assert rc == 0
    assert capsys.readouterr().out == BASE


def test_diff_changed_files_prints_wdiff_notation(files, capsys):
    tmp, write = files
    rc = main(["diff", write("a.md", BASE), write("b.md", OURS)])
    out = capsys.readouterr().out
    assert rc == 1
    assert "[-quick-]" in out
    assert "{+swift+}" in out


def test_missing_input_file_exits_two(files, capsys):
    tmp, write = files
    rc = main(["merge", str(tmp / "absent.md"), write("b.md", BASE), write("t.md", THEIRS)])
    assert rc == 2
    assert "error" in capsys.readouterr().err


def test_version_matches_package(capsys):
    assert main([]) == 2  # no subcommand: help on stderr, exit 2
    with pytest.raises(SystemExit) as excinfo:
        main(["--version"])
    assert excinfo.value.code == 0
    assert capsys.readouterr().out.strip() == f"prosemend {__version__}"
