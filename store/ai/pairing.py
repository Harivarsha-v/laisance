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


def explain(base, cand):
    shared = set(base.color_list) & set(cand.color_list)
    if shared:
        reason = REASONS["tonal"].format(c=sorted(shared)[0])
    else:
        reason = REASONS["color"].format(c=cand.color_list[0].title() if cand.color_list else "Its colour")
    if base.style == cand.style:
        reason += f", {REASONS['style'].format(s=cand.get_style_display().lower())}"
    return reason


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
