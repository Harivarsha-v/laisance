"""Turns a shopper's free text into structured intent.

"black jacket for him under $120" ->
    Intent(department="men", colors=["black"], categories=["coats"], budget_max=120)
"""

import re
from dataclasses import asdict, dataclass, field

from .lexicon import (
    CATEGORY_ALIASES,
    COLOR_ALIASES,
    DEPARTMENT_ALIASES,
    OCCASION_PRIORITY,
    OCCASION_TRIGGERS,
    OCCASIONS,
    SEASON_ALIASES,
)
from .text import stem, tokens, words

# "$10,000", "10000", "10k", "2.5k"
_MONEY = r"\$?\s*(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?\s*k\b|\d{1,7}(?:\.\d{1,2})?)\s*(?:\$|usd|dollars?|bucks)?"
_BETWEEN = re.compile(rf"(?:between|from)\s+{_MONEY}\s+(?:and|to|-)\s+{_MONEY}")
_UNDER = re.compile(rf"(?:under|below|less than|max(?:imum)?|up to|no more than|within|<|budget(?: of| is)?)\s*{_MONEY}")
_OVER = re.compile(rf"(?:over|above|more than|at least|min(?:imum)?|>)\s*{_MONEY}")
_BUDGET_AFTER = re.compile(rf"{_MONEY}\s*(?:budget|max|or less|tops)")

GREETINGS = {"hi", "hello", "hey", "yo", "hiya", "sup", "morning", "hola"}
THANKS = {"thanks", "thank", "thx", "ty", "cheers", "perfect", "great", "awesome", "love"}
CHEAPER = {"cheaper", "less", "affordable", "cheap", "lower", "save", "lighter", "smaller"}
RAISE = {"raise", "higher", "increase", "splurge", "pricier", "expensive", "luxury"}
ANOTHER = {"another", "different", "else", "other", "more", "again", "alternative", "swap", "next"}
NEGATORS = {"no", "not", "without", "except", "avoid", "hate", "dont", "don't"}


@dataclass
class Intent:
    department: str | None = None
    occasion: str | None = None
    season: str | None = None
    colors: list = field(default_factory=list)
    avoid_colors: list = field(default_factory=list)
    categories: list = field(default_factory=list)
    budget_max: float | None = None
    budget_min: float | None = None
    keywords: list = field(default_factory=list)
    greeting: bool = False
    thanks: bool = False
    cheaper: bool = False
    another: bool = False
    raise_budget: bool = False
    any_color: bool = False

    def to_dict(self):
        return asdict(self)

    @property
    def has_shopping_signal(self):
        return any([self.department, self.occasion, self.season, self.colors, self.categories,
                    self.budget_max, self.budget_min, self.keywords])

    def chips(self):
        """Human-readable summary of what the AI understood."""
        out = []
        if self.occasion:
            out.append(f"For {OCCASIONS[self.occasion]['label']}")
        if self.department:
            out.append(self.department.title())
        out += [c.title() for c in self.colors]
        out += [f"No {c}" for c in self.avoid_colors]
        out += [c.replace("-", " ").title() for c in self.categories]
        if self.season:
            out.append(self.season.title())
        if self.budget_min and self.budget_max:
            out.append(f"${self.budget_min:,.0f}–${self.budget_max:,.0f}")
        elif self.budget_max:
            out.append(f"Under ${self.budget_max:,.0f}")
        elif self.budget_min:
            out.append(f"Over ${self.budget_min:,.0f}")
        return out


def _money(m):
    m = m.replace(",", "").replace(" ", "").lower()
    return float(m[:-1]) * 1000 if m.endswith("k") else float(m)


def parse(text):
    text_l = (text or "").lower()
    ws = words(text_l)
    intent = Intent()

    if m := _BETWEEN.search(text_l):
        lo, hi = sorted([_money(m.group(1)), _money(m.group(2))])
        intent.budget_min, intent.budget_max = lo, hi
    else:
        if m := (_UNDER.search(text_l) or _BUDGET_AFTER.search(text_l)):
            intent.budget_max = _money(m.group(1))
        if m := _OVER.search(text_l):
            intent.budget_min = _money(m.group(1))

    consumed = set()
    occasions_seen = []
    negate_window = 0
    for w in ws:
        if w in NEGATORS:
            negate_window = 3
            continue
        negating = negate_window > 0
        negate_window = max(0, negate_window - 1)

        if w in COLOR_ALIASES:
            canon = COLOR_ALIASES[w]
            target = intent.avoid_colors if negating else intent.colors
            if canon not in target:
                target.append(canon)
            consumed.add(w)
        if w in DEPARTMENT_ALIASES and not intent.department:
            intent.department = DEPARTMENT_ALIASES[w]
            consumed.add(w)
        if w in OCCASION_TRIGGERS:
            occasions_seen.append(OCCASION_TRIGGERS[w])
            consumed.add(w)
        if w in SEASON_ALIASES and not intent.season:
            intent.season = SEASON_ALIASES[w]
        cat = CATEGORY_ALIASES.get(w) or CATEGORY_ALIASES.get(stem(w))
        if cat and cat not in intent.categories and not negating:
            intent.categories.append(cat)

    if occasions_seen:
        intent.occasion = min(occasions_seen, key=OCCASION_PRIORITY.index)
        if not intent.season:
            # "beach wedding" -> wedding, but dressed for summer
            intent.season = next((OCCASIONS[o]["season"] for o in occasions_seen if OCCASIONS[o].get("season")), None)

    wset = set(ws)
    intent.keywords = [t for t in tokens(text_l)
                       if t not in consumed and stem(t) not in consumed and t not in CHEAPER | ANOTHER | RAISE
                       and t not in {"colour", "color", "fine", "any", "matter"}]
    intent.raise_budget = bool(wset & RAISE)
    intent.any_color = "any" in wset and bool(wset & {"colour", "color", "colours", "colors"})
    intent.greeting = bool(wset & GREETINGS) and len(ws) <= 4
    intent.thanks = bool(wset & THANKS) and len(ws) <= 5 and not intent.has_shopping_signal
    intent.cheaper = bool(wset & CHEAPER) and not intent.budget_max
    intent.another = bool(wset & ANOTHER)
    return intent


def merge(previous, current):
    """Follow-up messages ("in black", "cheaper", "for him") refine the last request."""
    if not previous:
        return current
    prev = Intent(**previous)
    if current.occasion or current.categories:
        # a fresh request: keep only the department if none was given
        current.department = current.department or prev.department
        return current
    merged = Intent(**previous)
    merged.department = current.department or prev.department
    merged.colors = [] if current.any_color else (current.colors or prev.colors)
    merged.avoid_colors = [] if current.any_color else list({*prev.avoid_colors, *current.avoid_colors} - set(current.colors))
    merged.season = current.season or prev.season
    merged.budget_max = current.budget_max or prev.budget_max
    merged.budget_min = current.budget_min or prev.budget_min
    merged.keywords = current.keywords or prev.keywords
    merged.cheaper, merged.another = current.cheaper, current.another
    merged.raise_budget, merged.any_color = current.raise_budget, current.any_color
    merged.greeting = merged.thanks = False
    return merged
