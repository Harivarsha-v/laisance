"""Scores for how well two garments go together: colour, style and season."""

from itertools import product as pairs

from .lexicon import GOOD_PAIRS, NEUTRALS

STYLE_AFFINITY = {
    frozenset(["casual", "street"]): 0.8,
    frozenset(["work", "formal"]): 0.85,
    frozenset(["evening", "formal"]): 0.9,
    frozenset(["casual", "work"]): 0.6,
    frozenset(["casual", "evening"]): 0.55,
    frozenset(["sport", "street"]): 0.7,
    frozenset(["sport", "casual"]): 0.6,
    frozenset(["street", "evening"]): 0.5,
}


def color_pair(a, b):
    if a in NEUTRALS and b in NEUTRALS:
        return 0.85 if a != b else 0.75
    if a in NEUTRALS or b in NEUTRALS:
        return 0.9
    if a == b:
        return 0.45  # tonal, works but bold
    if frozenset([a, b]) in GOOD_PAIRS:
        return 0.8
    return 0.25


def color_harmony(colors_a, colors_b):
    if not colors_a or not colors_b:
        return 0.5
    return max(color_pair(a, b) for a, b in pairs(colors_a, colors_b))


def style_compat(a, b):
    if a == b:
        return 1.0
    return STYLE_AFFINITY.get(frozenset([a, b]), 0.3)


def season_compat(a, b):
    if a == b or "all" in (a, b):
        return 1.0
    if "transitional" in (a, b):
        return 0.7
    return 0.1  # summer with winter


def best_color(product, preferred):
    """The product colour to show: the shopper's preferred one if it has it."""
    for c in preferred or []:
        if c in product.color_list:
            return c
    return product.color_list[0] if product.color_list else ""
