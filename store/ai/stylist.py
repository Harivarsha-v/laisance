"""The AI stylist: a conversational outfit builder.

Each turn it parses the message into an intent, merges it with the
conversation so far (so "make it cheaper" or "in black" refine the last
look), then assembles an outfit slot by slot, scoring every candidate for
occasion fit, colour harmony with pieces already chosen, the shopper's
colour preferences, season and budget.
"""

import random

from django.utils.html import escape

from ..currency import format_price
from ..models import Product
from .harmony import best_color, color_harmony, season_compat, style_compat
from .intent import merge, parse
from .lexicon import OCCASIONS
from .search import get_index, passes_filters, smart_search
from .text import expand, stem

SLOT_NAMES = {"top": "top", "bottom": "bottoms", "one_piece": "dress", "outerwear": "layer", "shoes": "shoes", "accessory": "finishing touch"}
# share of the budget each slot is allowed to use
OPTIONAL_SLOTS = {"accessory", "outerwear"}
BUDGET_SHARE = {"outerwear": 0.35, "one_piece": 0.5, "top": 0.22, "bottom": 0.25, "shoes": 0.25, "accessory": 0.15}

INTROS = [
    "For {occ}, I would suggest this.",
    "Here is how I'd dress you for {occ}.",
    "For {occ}, something like this:",
    "A beautiful occasion. For {occ}:",
]
LINKERS = {
    "outerwear": ["Over it, the {name}{color}", "Layer the {name}{color} over the shoulders"],
    "top": ["begin with the {name}{color}", "the {name}{color} close to the skin"],
    "bottom": ["with the {name}{color}", "paired with the {name}{color}"],
    "one_piece": ["the {name}{color} sets the tone", "let the {name}{color} speak first"],
    "shoes": ["the {name}{color} underfoot", "finished with the {name}{color}"],
    "accessory": ["and the {name}{color} as the final gesture", "with the {name}{color} to complete it"],
}
WHY = {
    "wedding": "Elegant without ever upstaging the couple.",
    "work": "Composed and assured, and comfortable from the first meeting to the last.",
    "date": "Quietly seductive, and easy to move in.",
    "party": "It catches the light, and holds the room.",
    "beach": "Fabrics that breathe in the heat and fall beautifully in the breeze.",
    "winter": "Warmth without weight, and nothing superfluous.",
    "weekend": "Unhurried and easy, yet unmistakably considered.",
    "street": "Relaxed lines with a measure of nonchalance.",
}
HELP = (
    "I'm your personal stylist. Tell me the occasion and I'll compose a complete look from the collection. "
    "You might say <em>\"a wedding in Capri, under $10,000\"</em>, <em>\"the office, for him\"</em> or "
    "<em>\"a winter evening, in black\"</em>. Then refine it with <em>\"a lighter budget\"</em>, "
    "<em>\"another look\"</em> or <em>\"in navy\"</em>."
)
STARTERS = ["A wedding guest look under $10,000", "The office, for him", "Dinner in Paris, in black", "A week on the Riviera"]


def _fmt_color(color):
    return f" in {color}" if color else ""


class Stylist:
    def __init__(self, state=None):
        self.state = state or {}

    # ---- public -------------------------------------------------------
    def reply(self, message):
        current = parse(message)
        previous = self.state.get("intent")

        if current.greeting and not current.has_shopping_signal:
            return self._respond(f"Hey! {HELP}", suggestions=STARTERS)
        if current.thanks:
            return self._respond("With pleasure. Shall I compose another look, or dress you for a different occasion?",
                                 suggestions=["Another look", "Something for the weekend"])

        intent = merge(previous, current)
        is_follow_up = bool(previous) and not (current.occasion or current.categories)
        tweaks = intent.another or intent.cheaper or intent.raise_budget or intent.any_color
        if not intent.has_shopping_signal and not (is_follow_up and tweaks):
            return self._respond(f"I didn't quite catch the occasion. {HELP}", suggestions=STARTERS)

        if intent.cheaper and self.state.get("last_total"):
            intent.budget_max = round(self.state["last_total"] * 0.75)
        if intent.raise_budget:
            intent.budget_max = round((intent.budget_max or self.state.get("last_total") or 8000) * 1.4)

        # asked for specific items ("black jeans") rather than an outfit
        if intent.categories and not intent.occasion:
            return self._items(intent, message)

        if not intent.occasion:
            intent.occasion = "weekend"
        if not intent.department:
            self.state["intent"] = intent.to_dict()
            return self._respond(f"Lovely, {OCCASIONS[intent.occasion]['label']}. Shall I dress her, or him?",
                                 suggestions=["For her", "For him"])

        shown = set(self.state.get("shown", [])) if is_follow_up and intent.another else set()
        variant = self.state.get("variant", 0) + 1 if (is_follow_up and intent.another) else 0
        look = self._build_look(intent, exclude=shown, variant=variant)
        over_budget = None
        if not look and intent.budget_max:
            # nothing fits: show the closest look and be upfront about the price
            over_budget = intent.budget_max
            intent.budget_max = None
            look = self._build_look(intent, exclude=shown, variant=variant)
        if not look:
            return self._respond("I couldn't build a full look from what's in stock right now. Try another occasion?",
                                 suggestions=STARTERS)

        total = sum(float(i["product"].price) for i in look)
        self.state.update({
            "intent": intent.to_dict(),
            "shown": list(shown | {i["product"].id for i in look}),
            "variant": variant,
            "last_total": total,
        })
        text = self._describe(intent, look, total, variant)
        if over_budget:
            text += (f" I couldn't compose something I'd stand behind under ${over_budget:,.0f}, "
                     f"so this is the closest look, at <strong>{format_price(total)}</strong>.")
        return self._respond(
            text,
            look={"title": f"Look for {OCCASIONS[intent.occasion]['label']}", "items": look, "total": total},
            understood=intent.chips(),
            suggestions=self._suggestions(intent),
        )

    # ---- outfit building ---------------------------------------------
    def _candidates(self, intent):
        index = get_index()
        relaxed = type(intent)(**{**intent.to_dict(), "colors": [], "avoid_colors": intent.avoid_colors})
        return [p for p in index.products.values() if passes_filters(p, relaxed)]

    def _build_look(self, intent, exclude=frozenset(), variant=0):
        occ = OCCASIONS[intent.occasion]
        looks = occ["looks"][intent.department]
        slots = looks[variant % len(looks)]
        index = get_index()

        weights = expand(intent.keywords)
        for t in occ["terms"]:
            weights[stem(t)] = weights.get(stem(t), 0) + 0.6
        qvec = index.query_vector(weights)

        pool = self._candidates(intent)
        budget = intent.budget_max
        rng = random.Random(variant)
        chosen = []

        # only pieces whose style suits the occasion (no joggers at a wedding)
        pool = [p for p in pool if max(style_compat(p.style, s) for s in occ["styles"]) >= 0.55]

        for i, slot in enumerate(slots):
            options = [p for p in pool if p.category.slot == slot]
            if not options:
                if slot in OPTIONAL_SLOTS:
                    continue
                return None
            remaining_slots = slots[i + 1:]
            cap = None
            if budget:
                spent = sum(float(c["product"].price) for c in chosen)
                cheapest_rest = sum(
                    min((float(p.price) for p in pool if p.category.slot == s), default=0) for s in remaining_slots
                )
                cap = budget - spent - cheapest_rest
                options = [p for p in options if float(p.price) <= cap]
                if not options:
                    if slot in OPTIONAL_SLOTS:
                        continue
                    return None

            def score(p):
                s = index.similarity(qvec, p.id) * 1.5 if qvec else 0
                if p.style in occ["styles"]:
                    s += 1.0 if p.style == occ["styles"][0] else 0.6
                preferred = occ.get("prefer", {}).get(slot)
                if preferred and p.category.slug in preferred:
                    s += 0.5 - 0.1 * preferred.index(p.category.slug)
                if intent.colors:
                    s += 1.4 if set(p.color_list) & set(intent.colors) else 0
                if intent.season:
                    compat = season_compat(p.season, intent.season)
                    s += 0.4 * compat if compat > 0.5 else -1.5  # no wool scarves at the beach
                for c in chosen:
                    s += 0.5 * color_harmony(p.color_list, c["product"].color_list) / max(len(chosen), 1)
                if budget and BUDGET_SHARE.get(slot):
                    # gently prefer pieces that fit this slot's share of the budget
                    if float(p.price) > budget * BUDGET_SHARE[slot] * 1.4:
                        s -= 0.3
                if p.id in exclude:
                    s -= 2.0
                return s + rng.random() * 0.15 * (1 if variant else 0)

            best = max(options, key=score)
            if slot in OPTIONAL_SLOTS and score(best) < 0:
                continue  # better no accessory than the wrong one
            color = best_color(best, intent.colors)
            chosen.append({"product": best, "slot": slot, "color": color})
            pool = [p for p in pool if p.id != best.id]
        return chosen or None

    # ---- language ----------------------------------------------------
    def _describe(self, intent, look, total, variant):
        rng = random.Random(f"{intent.occasion}-{variant}-{len(look)}")
        occ_label = OCCASIONS[intent.occasion]["label"]
        parts = []
        for i, item in enumerate(look):
            p, slot = item["product"], item["slot"]
            phrase = rng.choice(LINKERS[slot]).format(name=f"<strong>{escape(p.name)}</strong>", color=_fmt_color(item["color"]))
            parts.append(phrase)
        sentence = ", ".join(parts)
        sentence = sentence[0].upper() + sentence[1:] + "."
        text = f"{rng.choice(INTROS).format(occ=occ_label)} {sentence} {WHY[intent.occasion]}"
        if intent.colors:
            misses = [i["product"].name for i in look if i["color"] not in intent.colors]
            if misses and len(misses) < len(look):
                text += f" I kept the {escape(misses[0])} in a neutral so the {intent.colors[0]} stands out."
            elif misses:
                text += f" I couldn't find {intent.colors[0]} pieces that fit, so I went with colours that work together."
        if intent.budget_max:
            text += f" It comes to <strong>{format_price(total)}</strong>, within your ${intent.budget_max:,.0f}."
        else:
            text += f" The complete look is <strong>{format_price(total)}</strong>."
        return text

    def _items(self, intent, message):
        result = smart_search(message, limit=6, intent=intent)
        self.state["intent"] = intent.to_dict()
        if not result.results:
            return self._respond("I couldn't find anything matching that. Want to loosen the budget or try another colour?",
                                 suggestions=["Show me everything new", "Any colour"])
        items = [{"product": p, "slot": p.category.slot, "color": best_color(p, intent.colors)} for p in result.products]
        names = ", ".join(escape(i["product"].name) for i in items[:3])
        return self._respond(
            f"Here are my top picks: {names}{' and more' if len(items) > 3 else ''}. "
            "Tell me the occasion and I'll build a full outfit around one of them.",
            look={"title": "Top picks", "items": items, "total": None},
            understood=intent.chips(),
            suggestions=["Style it for the office", "Style it for dinner", "A lighter budget"],
        )

    def _suggestions(self, intent):
        out = ["Another look", "A lighter budget"]
        if "black" not in intent.colors:
            out.append("In black")
        out.append("For him" if intent.department == "women" else "For her")
        return out

    def _respond(self, text, look=None, understood=None, suggestions=None):
        return {"text": text, "look": look, "understood": understood or [], "suggestions": suggestions or [], "state": self.state}


def serialise_look(look):
    """JSON-friendly version for the chat API."""
    from ..templatetags.store_extras import garment

    if not look:
        return None
    return {
        "title": look["title"],
        "total": look["total"],
        "total_display": format_price(look["total"]) if look["total"] else "",
        "items": [
            {
                "id": i["product"].id,
                "name": i["product"].name,
                "url": i["product"].get_absolute_url(),
                "price": format_price(i["product"].price),
                "slot": i["slot"],
                "color": i["color"],
                "category": i["product"].category.name,
                "art": str(garment(i["product"], label=False, color=i["color"])),
            }
            for i in look["items"]
        ],
    }
