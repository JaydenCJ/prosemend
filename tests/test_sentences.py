"""Sentence splitting: boundaries, guards, and lossless round-tripping."""

from prosemend.sentences import split_sentences


def roundtrip(text):
    parts = split_sentences(text)
    assert "".join(parts) == text
    return parts


def test_basic_split_keeps_trailing_space_with_sentence():
    assert roundtrip("One. Two.") == ["One. ", "Two."]


def test_question_and_exclamation_end_sentences():
    assert roundtrip("Why? Go! Done.") == ["Why? ", "Go! ", "Done."]


def test_abbreviations_do_not_split():
    parts = roundtrip("Use plain tools, e.g. diff3, etc. when possible.")
    assert len(parts) == 1


def test_single_initials_do_not_split():
    assert roundtrip("J. Smith wrote it. True.") == ["J. Smith wrote it. ", "True."]


def test_decimal_numbers_do_not_split():
    assert roundtrip("Pi is 3.14 exactly. No.") == ["Pi is 3.14 exactly. ", "No."]


def test_ordered_list_marker_does_not_split():
    # "1. item" at line start: the dot is a list marker, not a period.
    assert roundtrip("1. first item stays whole") == ["1. first item stays whole"]


def test_number_ending_a_real_sentence_still_splits():
    assert roundtrip("The answer is 42. Next one.") == [
        "The answer is 42. ",
        "Next one.",
    ]


def test_cjk_terminator_needs_no_following_space():
    assert roundtrip("これは文です。次の文。") == ["これは文です。", "次の文。"]


def test_text_without_terminator_is_one_sentence():
    assert roundtrip("# A heading with no period") == ["# A heading with no period"]
    assert split_sentences("") == []
