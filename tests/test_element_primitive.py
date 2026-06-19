"""Locks the shared count_element_distribution primitive.

career/health/wealth previously each hand-rolled the identical weighted
five-element tally (stem 1.0 / branch 0.5 / hidden stem 0.3). This pins the
weights and the zero-initialised full-Element result so the extraction can't
drift.
"""

from fatebridge.utils.data import (
    BRANCH_ELEMENTS,
    BRANCH_HIDDEN_STEMS,
    STEM_ELEMENTS,
    Element,
    count_element_distribution,
)


def _reference(pillars):
    counts = {e: 0.0 for e in Element}
    for stem, branch in pillars.values():
        counts[STEM_ELEMENTS[stem][0]] += 1.0
        counts[BRANCH_ELEMENTS[branch][0]] += 0.5
        for hidden in BRANCH_HIDDEN_STEMS.get(branch, []):
            counts[STEM_ELEMENTS[hidden][0]] += 0.3
    return counts


def test_matches_reference_weighting():
    pillars = {
        "year": ("庚", "午"),
        "month": ("辛", "巳"),
        "day": ("辛", "巳"),
        "hour": ("甲", "午"),
    }
    assert count_element_distribution(pillars) == _reference(pillars)


def test_result_includes_every_element_zero_initialised():
    counts = count_element_distribution({"day": ("甲", "子")})
    assert set(counts) == set(Element)
    # 甲(木)=1.0, 子 branch(水)=0.5, 子 hidden 癸(水)=0.3 -> 水=0.8
    assert counts[STEM_ELEMENTS["甲"][0]] == 1.0
    assert counts[Element.WATER] == 0.8
