"""End-to-end Markdown merges: the false-conflict killer and its edges."""

import pytest

from prosemend import MergeOptions, merge_text


def clean(base, ours, theirs, **kw):
    result = merge_text(base, ours, theirs, MergeOptions(**kw) if kw else None)
    assert result.clean, f"unexpected conflict:\n{result.text}"
    return result.text


def test_two_word_edits_on_the_same_line_merge_cleanly():
    # THE headline case: git and diff3 conflict here; prosemend must not.
    base = "The quick brown fox jumps over the lazy dog.\n"
    ours = "The swift brown fox jumps over the lazy dog.\n"
    theirs = "The quick brown fox leaps over the lazy dog.\n"
    assert clean(base, ours, theirs) == (
        "The swift brown fox leaps over the lazy dog.\n"
    )


def test_edit_versus_append_on_the_same_line_merges_cleanly():
    base = "Ship the draft today.\n"
    ours = "Ship the final draft today.\n"
    theirs = "Ship the draft today, please.\n"
    assert clean(base, ours, theirs) == "Ship the final draft today, please.\n"


def test_no_changes_returns_base_byte_identical():
    base = "# T\n\nSome *prose* here.\n\n```\ncode\n```\n"
    assert clean(base, base, base) == base


def test_same_edit_on_both_sides_is_clean():
    base = "colour\n"
    both = "color\n"
    assert clean(base, both, both) == "color\n"


def test_different_edits_to_the_same_word_conflict():
    base = "The quick fox.\n"
    result = merge_text(base, "The swift fox.\n", "The speedy fox.\n")
    assert result.conflicts == 1
    assert "<<<<<<< ours\nThe swift fox.\n" in result.text
    assert "=======\nThe speedy fox.\n>>>>>>> theirs\n" in result.text


def test_conflict_output_contains_full_lines_not_word_fragments():
    base = "alpha beta gamma delta\n"
    result = merge_text(base, "alpha BETA gamma delta\n", "alpha Beta gamma delta\n")
    assert result.conflicts == 1
    # Every conflict variant must be the complete line, so editors can parse it.
    assert "alpha BETA gamma delta\n" in result.text
    assert "alpha Beta gamma delta\n" in result.text


def test_edits_in_different_paragraphs_never_interact():
    base = "Para one is here.\n\nPara two is here.\n"
    ours = "Para one is changed.\n\nPara two is here.\n"
    theirs = "Para one is here.\n\nPara two is different.\n"
    assert clean(base, ours, theirs) == (
        "Para one is changed.\n\nPara two is different.\n"
    )


def test_whitespace_only_divergence_is_auto_resolved():
    # Ours reflowed the line, theirs added a double space: same words.
    base = "one two three\n"
    ours = "one\ntwo three\n"
    theirs = "one  two three\n"
    result = merge_text(base, ours, theirs)
    assert result.clean
    assert result.auto_resolved == 1
    assert result.text == ours


def test_code_fence_edits_merge_line_wise_not_word_wise():
    base = "```py\nx = compute(1)\n```\n"
    ours = "```py\nx = compute(2)\n```\n"
    theirs = "```py\ny = compute(1)\n```\n"
    # Both edited the same code line differently: this MUST conflict even
    # though the word-level union would be "y = compute(2)".
    result = merge_text(base, ours, theirs)
    assert result.conflicts == 1
    assert "x = compute(2)\n" in result.text
    assert "y = compute(1)\n" in result.text


def test_distinct_code_lines_merge_cleanly():
    base = "```py\na = 1\nb = 2\n```\n"
    ours = "```py\na = 10\nb = 2\n```\n"
    theirs = "```py\na = 1\nb = 20\n```\n"
    assert clean(base, ours, theirs) == "```py\na = 10\nb = 20\n```\n"


def test_table_rows_merge_row_wise():
    base = "| k | v |\n|---|---|\n| a | 1 |\n| b | 2 |\n"
    ours = "| k | v |\n|---|---|\n| a | 9 |\n| b | 2 |\n"
    theirs = "| k | v |\n|---|---|\n| a | 1 |\n| b | 8 |\n"
    assert clean(base, ours, theirs) == (
        "| k | v |\n|---|---|\n| a | 9 |\n| b | 8 |\n"
    )


def test_link_atomicity_conflicts_on_competing_url_edits():
    base = "Read [the guide](https://example.test/v1) first.\n"
    ours = "Read [the guide](https://example.test/v2) first.\n"
    theirs = "Read [the full guide](https://example.test/v1) first.\n"
    # The whole link is one atom, so text-edit vs url-edit is a true conflict.
    result = merge_text(base, ours, theirs)
    assert result.conflicts == 1


def test_sentence_granularity_conflicts_inside_one_sentence():
    base = "The quick fox jumps. It was tired.\n"
    ours = "The swift fox jumps. It was tired.\n"
    theirs = "The quick fox leaps. It was tired.\n"
    # Word granularity merges this cleanly; sentence granularity must not.
    assert merge_text(base, ours, theirs).clean
    strict = merge_text(base, ours, theirs, MergeOptions(granularity="sentence"))
    assert strict.conflicts == 1


def test_sentence_granularity_merges_edits_in_different_sentences():
    base = "First sentence here. Second sentence here.\n"
    ours = "First sentence changed. Second sentence here.\n"
    theirs = "First sentence here. Second sentence altered.\n"
    assert clean(base, ours, theirs, granularity="sentence") == (
        "First sentence changed. Second sentence altered.\n"
    )


def test_line_granularity_reproduces_diff3_false_conflict():
    # Sanity: with --granularity line prosemend behaves like classic diff3,
    # which is exactly the false conflict the default mode eliminates.
    base = "The quick brown fox jumps over the lazy dog.\n"
    ours = "The swift brown fox jumps over the lazy dog.\n"
    theirs = "The quick brown fox leaps over the lazy dog.\n"
    result = merge_text(base, ours, theirs, MergeOptions(granularity="line"))
    assert result.conflicts == 1


def test_favor_ours_resolves_all_conflicts():
    base = "pick a word\n"
    result = merge_text(
        base, "pick our word\n", "pick their word\n", MergeOptions(favor="ours")
    )
    assert result.clean
    assert result.text == "pick our word\n"


def test_favor_union_keeps_both_insertions():
    base = "- item one\n"
    ours = "- item one\n- from ours\n"
    theirs = "- item one\n- from theirs\n"
    result = merge_text(base, ours, theirs, MergeOptions(favor="union"))
    assert result.clean
    assert "- from ours\n" in result.text
    assert "- from theirs\n" in result.text


def test_cjk_prose_merges_at_character_level():
    base = "私は猫が好きです。\n"
    ours = "私は犬が好きです。\n"  # cat -> dog
    theirs = "私は猫が大好きです。\n"  # like -> love
    assert clean(base, ours, theirs) == "私は犬が大好きです。\n"


def test_front_matter_edits_merge_line_wise():
    base = "---\ntitle: Draft\ndate: 2026-07-01\n---\nBody text.\n"
    ours = "---\ntitle: Final\ndate: 2026-07-01\n---\nBody text.\n"
    theirs = "---\ntitle: Draft\ndate: 2026-07-12\n---\nBody text.\n"
    assert clean(base, ours, theirs) == (
        "---\ntitle: Final\ndate: 2026-07-12\n---\nBody text.\n"
    )


def test_paragraph_added_by_each_side_in_different_places():
    base = "First.\n\nLast.\n"
    ours = "Intro.\n\nFirst.\n\nLast.\n"
    theirs = "First.\n\nLast.\n\nOutro.\n"
    assert clean(base, ours, theirs) == "Intro.\n\nFirst.\n\nLast.\n\nOutro.\n"


def test_custom_labels_appear_in_markers():
    base = "word\n"
    opts = MergeOptions(label_ours="draft-a.md", label_theirs="draft-b.md")
    result = merge_text(base, "ours\n", "theirs\n", opts)
    assert "<<<<<<< draft-a.md\n" in result.text
    assert ">>>>>>> draft-b.md\n" in result.text


def test_empty_base_divergent_sides_conflict():
    result = merge_text("", "version a\n", "version b\n")
    assert result.conflicts == 1


def test_invalid_options_are_rejected():
    with pytest.raises(ValueError):
        MergeOptions(granularity="paragraph")
    with pytest.raises(ValueError):
        MergeOptions(favor="mine")
    with pytest.raises(ValueError):
        MergeOptions(style="xml")
    with pytest.raises(ValueError):
        MergeOptions(marker_size=1)
