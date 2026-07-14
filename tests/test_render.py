"""Conflict rendering: line widening, coalescing, and marker styles."""

from prosemend.render import Conflict, MarkerStyle, render


STYLE = MarkerStyle()


def test_mid_line_conflict_is_widened_to_the_full_line():
    pieces = ["The ", Conflict("swift", "quick", "speedy"), " fox.\n"]
    text, blocks = render(pieces, STYLE)
    assert blocks == 1
    assert text == (
        "<<<<<<< ours\n"
        "The swift fox.\n"
        "=======\n"
        "The speedy fox.\n"
        ">>>>>>> theirs\n"
    )


def test_two_conflicts_on_one_line_coalesce_into_one_block():
    pieces = [
        "a ",
        Conflict("X", "x", "Y"),
        " mid ",
        Conflict("P", "p", "Q"),
        " z\n",
    ]
    text, blocks = render(pieces, STYLE)
    assert blocks == 1
    assert "a X mid P z\n" in text
    assert "a Y mid Q z\n" in text


def test_conflicts_on_different_lines_stay_separate():
    pieces = ["a ", Conflict("X", "x", "Y"), " b\nc ", Conflict("P", "p", "Q"), " d\n"]
    text, blocks = render(pieces, STYLE)
    assert blocks == 2


def test_diff3_style_includes_base_section():
    style = MarkerStyle(style="diff3", label_base="ancestor")
    text, _ = render([Conflict("o\n", "b\n", "t\n")], style)
    assert "||||||| ancestor\n" in text
    assert "b\n" in text


def test_git_style_omits_base_section():
    text, _ = render([Conflict("o\n", "b\n", "t\n")], STYLE)
    assert "|||||||" not in text
    assert "b\n=======" not in text


def test_custom_labels_and_marker_size():
    style = MarkerStyle(label_ours="a.md", label_theirs="b.md", marker_size=11)
    text, _ = render([Conflict("o\n", "b\n", "t\n")], style)
    assert "<" * 11 + " a.md\n" in text
    assert ">" * 11 + " b.md\n" in text
    assert "<" * 12 not in text


def test_conflict_at_end_of_file_without_newline_gets_padded():
    # Markers must be parseable lines even when the file lacks a final newline.
    text, blocks = render(["start ", Conflict("A", "b", "B")], STYLE)
    assert blocks == 1
    assert text.endswith(">>>>>>> theirs\n")
    assert "start A\n" in text and "start B\n" in text


def test_empty_side_renders_as_empty_section():
    # Pure insertion vs nothing: the empty side has no body lines, like git.
    text, _ = render([Conflict("new text\n", "", "")], STYLE)
    assert "<<<<<<< ours\nnew text\n=======\n>>>>>>> theirs\n" == text


def test_multiline_conflict_variant_is_kept_intact():
    text, blocks = render([Conflict("l1\nl2\n", "b\n", "t\n")], STYLE)
    assert blocks == 1
    assert "l1\nl2\n=======" in text
