"""The diff3 core: gap classification over plain token sequences."""

from prosemend.diff3 import Conflicted, Resolved, merge_tokens


def merged_tokens(regions):
    """Flatten regions, asserting none conflicted."""
    out = []
    for r in regions:
        assert isinstance(r, Resolved), f"unexpected conflict: {r}"
        out.extend(r.tokens)
    return out


def test_identical_inputs_pass_through():
    base = list("abcdef")
    regions = merge_tokens(base, base, base)
    assert merged_tokens(regions) == base


def test_non_overlapping_changes_both_apply():
    base = list("abcdef")
    ours = list("Xbcdef")  # change at the front
    theirs = list("abcdeY")  # change at the back
    assert merged_tokens(merge_tokens(base, ours, theirs)) == list("XbcdeY")


def test_identical_change_on_both_sides_is_clean():
    base = list("abcdef")
    changed = list("abZdef")
    assert merged_tokens(merge_tokens(base, changed, changed)) == changed


def test_different_changes_to_same_token_conflict():
    base = list("abcdef")
    regions = merge_tokens(base, list("abXdef"), list("abYdef"))
    conflicts = [r for r in regions if isinstance(r, Conflicted)]
    assert len(conflicts) == 1
    assert conflicts[0] == Conflicted(("c",), ("X",), ("Y",))


def test_different_inserts_at_same_point_conflict():
    # diff3 semantics: two different insertions at one anchor are ambiguous.
    base = list("ab")
    regions = merge_tokens(base, list("aXb"), list("aYb"))
    assert any(isinstance(r, Conflicted) for r in regions)


def test_identical_inserts_at_same_point_are_clean():
    base = list("ab")
    ours = theirs = list("aXb")
    assert merged_tokens(merge_tokens(base, ours, theirs)) == ours


def test_delete_versus_edit_conflicts():
    base = list("abc")
    ours = list("ac")  # deleted b
    theirs = list("aXc")  # edited b
    regions = merge_tokens(base, ours, theirs)
    assert any(isinstance(r, Conflicted) for r in regions)


def test_both_delete_same_token_is_clean():
    base = list("abc")
    both = list("ac")
    assert merged_tokens(merge_tokens(base, both, both)) == both


def test_ours_appends_theirs_prepends_both_apply():
    base = list("mm")
    ours = list("mmA")
    theirs = list("Bmm")
    assert merged_tokens(merge_tokens(base, ours, theirs)) == list("BmmA")


def test_repeated_tokens_do_not_confuse_alignment():
    # 'the' appears many times; autojunk=False keeps alignment exact.
    base = "the a the b the c the d the e the f the g the".split()
    ours = list(base)
    ours[1] = "A"
    theirs = list(base)
    theirs[-2] = "G"
    expected = list(base)
    expected[1] = "A"
    expected[-2] = "G"
    assert merged_tokens(merge_tokens(base, ours, theirs)) == expected
