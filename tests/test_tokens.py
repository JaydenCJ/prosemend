"""Prose tokenizer: atom boundaries and the lossless round-trip invariant."""

from prosemend.tokens import is_cjk, tokenize_prose


def roundtrip(text):
    tokens = tokenize_prose(text)
    assert "".join(tokens) == text
    return tokens


def test_words_and_spaces_are_separate_atoms():
    assert roundtrip("the quick fox") == ["the", " ", "quick", " ", "fox"]


def test_apostrophes_and_hyphens_stay_inside_words():
    # Splitting "don't" or "well-known" would let a merge tear a word apart.
    assert roundtrip("don't well-known can’t") == [
        "don't", " ", "well-known", " ", "can’t",
    ]


def test_runs_of_identical_punctuation_stay_together():
    # '**' and '---' must survive as units or emphasis/hr markers get split.
    assert roundtrip("**bold** --- done") == [
        "**", "bold", "**", " ", "---", " ", "done",
    ]


def test_inline_code_span_is_one_atom():
    assert roundtrip("run `git merge` now") == [
        "run", " ", "`git merge`", " ", "now",
    ]


def test_unclosed_backticks_degrade_to_punctuation():
    assert roundtrip("a ` b") == ["a", " ", "`", " ", "b"]


def test_link_is_one_atom():
    assert roundtrip("see [the docs](https://example.test/a) ok") == [
        "see", " ", "[the docs](https://example.test/a)", " ", "ok",
    ]


def test_image_is_one_atom():
    tokens = roundtrip("![alt text](img.png) tail")
    assert tokens[0] == "![alt text](img.png)"


def test_image_inside_link_uses_one_nesting_level():
    text = "[![badge](b.svg)](https://example.test)"
    assert roundtrip(text) == [text]


def test_bracket_without_destination_is_not_a_link():
    # "[citation needed]" has no (...) — the words inside must stay mergeable.
    assert roundtrip("[citation needed]") == ["[", "citation", " ", "needed", "]"]


def test_autolink_is_one_atom():
    assert roundtrip("<https://example.test/x> end")[0] == "<https://example.test/x>"


def test_angle_bracket_comparison_is_not_an_autolink():
    assert roundtrip("a < b") == ["a", " ", "<", " ", "b"]


def test_cjk_characters_are_single_atoms():
    # Character-level atoms let Chinese and Japanese prose merge without a
    # word segmenter.
    assert roundtrip("合并中文") == ["合", "并", "中", "文"]
    assert all(is_cjk(c) for c in "合并中文ひらカナ")


def test_newlines_are_individual_atoms():
    assert roundtrip("a\nb\n") == ["a", "\n", "b", "\n"]
    assert tokenize_prose("") == []
