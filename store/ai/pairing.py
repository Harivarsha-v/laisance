"""'Complete the look': picks pieces from other outfit slots that go with a product."""

from ..models import Product, Slot
from .harmony import color_harmony, season_compat, style_compat

COMPLEMENTS = {
    Slot.TOP: [Slot.BOTTOM, Slot.SHOES, Slot.OUTERWEAR],
    Slot.BOTTOM: [Slot.TOP, Slot.SHOES, Slot.OUTERWEAR],
    Slot.ONE_PIECE: [Slot.SHOES, Slot.ACCESSORY, Slot.OUTERWEAR],
    Slot.OUTERWEAR: [Slot.TOP, Slot.BOTTOM, Slot.SHOES],
    Slot.SHOES: [Slot.TOP, Slot.BOTTOM, Slot.ACCESSORY],
    Slot.ACCESSORY: [Slot.TOP, Slot.BOTTOM, Slot.SHOES],
}

REASONS = {
    "color": "{c} keeps the palette easy",
    "tonal": "a tonal {c} for a polished, head-to-toe feel",
    "style": "same {s} mood",
    "season": "right weight for {season}",
}


def pair_score(base, cand):
    """0..~1: colour harmony matters most, then style, then season, then similar price tier."""
    price_ratio = min(base.price, cand.price) / max(base.price, cand.price)
    return (
        0.45 * color_harmony(base.color_list, cand.color_list)
        + 0.3 * style_compat(base.style, cand.style)
        + 0.15 * season_compat(base.season, cand.season)
        + 0.1 * float(price_ratio)
    )


SLOT_REASONS = {
    "top": "{colour} close to the skin, under the {base}",
    "bottom": "{colour} below, to let the {base} lead",
    "one_piece": "{colour}, a single line beside the {base}",
    "outerwear": "a {colour} layer over the {base}",
    "shoes": "{colour} underfoot, to ground the look",
    "accessory": "{colour}, as the final gesture",
}


def explain(base, cand):
    """A short reason written for the candidate's role in the outfit, so each suggestion reads differently."""
    shared = set(base.color_list) & set(cand.color_list)
    colour = sorted(shared)[0] if shared else (cand.color_list[0] if cand.color_list else "a quiet colour")
    if shared:
        colour = f"tonal {colour}"
    template = SLOT_REASONS.get(cand.category.slot, "{colour}, chosen to sit with the {base}")
    if base.category.slot in ("accessory", "shoes") and cand.category.slot in ("top", "bottom", "one_piece"):
        template = "{colour}, to wear with the {base}"  # clothes aren't "under" a scarf or a shoe
    noun = next((w for w in reversed(base.name.split()) if w.isalpha()), "piece").lower()  # "Slip Dress" -> "dress"
    return template.format(colour=colour, base=noun)


def complete_the_look(product, n=3):
    candidates = (
        Product.objects.select_related("category")
        .filter(department=product.department)
        .exclude(pk=product.pk)
    )
    by_slot = {}
    for c in candidates:
        by_slot.setdefault(c.category.slot, []).append(c)

    picks = []
    for slot in COMPLEMENTS[product.slot]:
        options = by_slot.get(slot, [])
        if not options:
            continue
        best = max(options, key=lambda c: (pair_score(product, c), -c.pk))
        picks.append({"product": best, "reason": explain(product, best), "score": round(pair_score(product, best), 2)})
        if len(picks) == n:
            break
    return picks
