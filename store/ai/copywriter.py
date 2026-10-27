"""Writes product descriptions and tags from a product's attributes.

A small template-based language generator: it picks phrases that fit the
garment's slot, style, season, material and colours, so every product gets
copy in the house voice without anyone writing it by hand.
"""

import random

OPENERS = {
    "top": ["A piece that rewards a second look.", "Quiet, precise and endlessly wearable.", "The kind of layer that becomes a signature."],
    "bottom": ["Cut to follow the body, never to hold it.", "A line that falls exactly as it should.", "Tailoring that forgets it is tailored."],
    "one_piece": ["A single gesture, complete in itself.", "Effortless from the first moment it is worn.", "Made to move, and to be remembered."],
    "outerwear": ["The last layer, and the one that is noticed first.", "Architecture you can live in.", "A coat to keep for decades."],
    "shoes": ["Made on the last for a light, sure step.", "Grounded and graceful in equal measure.", "Finished by hand, built to be resoled."],
    "accessory": ["The detail that completes the silhouette.", "An object as much as an accessory.", "Small in scale, considerable in presence."],
}

STYLE_LINES = {
    "casual": ["Unhurried by nature,", "Relaxed without ever being casual,"],
    "work": ["Composed for the working day,", "Assured and exact,"],
    "formal": ["Made for the occasions that matter,", "Ceremonial in spirit,"],
    "evening": ["Conceived for the evening,", "Luminous after dark,"],
    "sport": ["Engineered for movement,", "Light and responsive,"],
    "street": ["With an edge of nonchalance,", "Self-possessed and modern,"],
}

STYLE_ENDINGS = {
    "casual": ["it moves easily from a long lunch to the drive home.", "it asks for nothing more than a good pair of shoes."],
    "work": ["it carries the day with quiet authority.", "it is as considered at six in the evening as at nine."],
    "formal": ["it brings poise without ceremony.", "it is elegant without ever trying to be."],
    "evening": ["it catches the light and holds it.", "it is the piece that will be asked about."],
    "sport": ["it keeps pace without losing its line.", "it stays composed in motion."],
    "street": ["it is best worn with a certain indifference.", "it lends attitude to the simplest look."],
}

SEASON_LINES = {
    "summer": "Light and breathable, for warm days and long evenings.",
    "winter": "Warm without weight through the colder months.",
    "transitional": "Weighted for the in-between seasons.",
    "all": "A piece for every season of the year.",
}

STYLE_TAGS = {
    "casual": ["weekend", "everyday"],
    "work": ["office", "tailored"],
    "formal": ["wedding guest", "occasion"],
    "evening": ["date night", "party"],
    "sport": ["active"],
    "street": ["city", "relaxed"],
}
SEASON_TAGS = {"summer": ["summer", "lightweight"], "winter": ["winter", "warm"], "transitional": ["layering"], "all": []}


def _material_line(material):
    if not material:
        return ""
    line = f"In {material[0].lower() + material[1:]}"
    return line + ("." if "hand" in material.lower() else ", finished by hand.")


def _color_line(colors):
    if not colors:
        return ""
    if len(colors) == 1:
        return f"Offered in {colors[0]}."
    return f"Offered in {', '.join(colors[:-1])} and {colors[-1]}."


def write_copy(product, variant=0):
    rng = random.Random(f"{product.name}-{variant}")
    slot = product.category.slot if product.category_id else "top"
    style = product.style or "casual"
    season = product.season or "all"
    colors = product.color_list

    sentences = [
        rng.choice(OPENERS.get(slot, OPENERS["top"])),
        f"{rng.choice(STYLE_LINES[style])} {rng.choice(STYLE_ENDINGS[style])}",
        _material_line(product.material),
        SEASON_LINES[season],
        _color_line(colors),
    ]
    if getattr(product, "is_limited", False):
        sentences.append("Made in a limited edition, allocated one per client.")
    description = " ".join(s for s in sentences if s)

    tags = [product.category.name.lower()] if product.category_id else []
    tags += STYLE_TAGS[style] + SEASON_TAGS[season] + colors
    if product.material:
        tags += [w.lower().strip(",") for w in product.material.split()[:2] if len(w) > 3]
    seen, unique = set(), []
    for t in tags:
        if t not in seen:
            seen.add(t)
            unique.append(t)
    return {"description": description, "tags": unique}
