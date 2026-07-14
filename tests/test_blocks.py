"""Block segmentation: kinds, boundaries, and lossless round-tripping."""

from prosemend.blocks import segment


def kinds(text):
    return [b.kind for b in segment(text)]


def roundtrip(text):
    blocks = segment(text)
    assert "".join(b.text for b in blocks) == text
    return blocks


def test_paragraphs_split_on_blank_lines():
    assert kinds("one\n\ntwo\n") == ["prose", "blank", "prose"]


def test_backtick_fence_is_one_atomic_block():
    blocks = roundtrip("before\n\n```py\nx = 1\n```\n\nafter\n")
    assert [b.kind for b in blocks] == ["prose", "blank", "fence", "blank", "prose"]
    assert blocks[2].text == "```py\nx = 1\n```\n"


def test_fence_close_requires_at_least_opening_length():
    # ```` inside a ``` block would close it; a shorter run must not.
    blocks = roundtrip("````\n```\nstill code\n````\n")
    assert [b.kind for b in blocks] == ["fence"]


def test_unclosed_fence_swallows_rest_of_file():
    blocks = roundtrip("```\nnever closed\nmore\n")
    assert [b.kind for b in blocks] == ["fence"]


def test_backtick_info_string_with_backtick_is_not_a_fence():
    # CommonMark: a backtick fence's info string may not contain backticks.
    assert kinds("``` `x` ```\n") == ["prose"]


def test_blank_lines_inside_fence_do_not_split_it():
    blocks = roundtrip("```\na\n\nb\n```\n")
    assert [b.kind for b in blocks] == ["fence"]


def test_pipe_table_is_one_atomic_block():
    text = "| a | b |\n|---|---|\n| 1 | 2 |\n"
    blocks = roundtrip("intro\n" + text)
    assert [b.kind for b in blocks] == ["prose", "table"]
    assert blocks[1].text == text


def test_front_matter_at_document_start_is_atomic():
    blocks = roundtrip("---\ntitle: x\n---\nbody\n")
    assert [b.kind for b in blocks] == ["front_matter", "prose"]


def test_unclosed_front_matter_is_not_front_matter():
    # A lone '---' opener is a thematic break, not YAML.
    assert kinds("---\nno closer here\n") != ["front_matter"]


def test_indented_code_after_blank_line_is_atomic():
    blocks = roundtrip("para\n\n    code line\n    code line 2\n")
    assert [b.kind for b in blocks] == ["prose", "blank", "indented_code"]


def test_indented_line_inside_paragraph_stays_prose():
    # Lazy list continuations look like indented code; they must merge as prose.
    assert kinds("- item\n    continuation\n") == ["prose"]


def test_complex_document_roundtrips_exactly():
    text = (
        "---\nkey: v\n---\n\n# Title\n\npara **bold** text\n\n"
        "| a |\n|---|\n\n```sh\nls\n```\n\n    indented\n\nend"
    )
    roundtrip(text)
    assert segment("") == []
