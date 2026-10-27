"""Smart search: a TF-IDF vector index over the catalogue plus intent-aware re-ranking.

The index is built in memory from the Product table and rebuilt automatically
whenever products change, so there is nothing to train or deploy.
"""

import math
from collections import Counter
from dataclasses import dataclass, field

from django.db.models import Count, Max

from ..models import Product
from .intent import Intent, parse
from .lexicon import OCCASIONS
from .text import expand, stem, tokens

# how much each product field counts when indexing
FIELD_WEIGHTS = {"name": 3, "category": 2, "tags": 2, "colors": 2, "material": 2, "style": 1, "season": 1, "description": 1}


class TfIdfIndex:
    def __init__(self, products):
        self.products = {p.id: p for p in products}
        docs = {pid: self._doc_terms(p) for pid, p in self.products.items()}
        n = len(docs) or 1
        df = Counter(t for terms in docs.values() for t in terms)
        self.idf = {t: math.log((n + 1) / (c + 1)) + 1 for t, c in df.items()}
        self.vectors = {pid: self._normalise({t: tf * self.idf[t] for t, tf in terms.items()}) for pid, terms in docs.items()}

    @staticmethod
    def _doc_terms(p):
        fields = {
            "name": p.name,
            "category": f"{p.category.name} {p.category.slug.replace('-', '')}",
            "tags": p.tags,
            "colors": p.colors,
            "material": p.material,
            "style": p.style,
            "season": p.season,
            "description": p.description,
        }
        terms = Counter()
        for f, text in fields.items():
            for t in tokens(text):
                terms[t] += FIELD_WEIGHTS[f]
        return terms

    @staticmethod
    def _normalise(vec):
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        return {t: v / norm for t, v in vec.items()}

    def query_vector(self, weights):
        return self._normalise({t: w * self.idf.get(t, 0) for t, w in weights.items() if t in self.idf})

    def similarity(self, qvec, pid):
        dvec = self.vectors[pid]
        return sum(w * dvec.get(t, 0) for t, w in qvec.items())


_cache = {"sig": None, "index": None}


def get_index():
    sig = tuple(Product.objects.aggregate(n=Count("id"), t=Max("updated")).values())
    if _cache["sig"] != sig:
        _cache["index"] = TfIdfIndex(Product.objects.select_related("category"))
        _cache["sig"] = sig
    return _cache["index"]


@dataclass
class SearchResult:
    query: str
    intent: Intent
    results: list = field(default_factory=list)  # [(product, score)]

    @property
    def products(self):
        return [p for p, _ in self.results]


def passes_filters(p, intent):
    if intent.department and p.department != intent.department:
        return False
    if intent.budget_max and float(p.price) > intent.budget_max:
        return False
    if intent.budget_min and float(p.price) < intent.budget_min:
        return False
    if intent.avoid_colors and set(p.color_list) <= set(intent.avoid_colors):
        return False
    return True


def score_product(index, qvec, p, intent):
    score = index.similarity(qvec, p.id) if qvec else 0.0
    if intent.categories:
        score += 0.6 if p.category.slug in intent.categories else -0.4
    if intent.colors:
        score += 0.35 if set(p.color_list) & set(intent.colors) else -0.2
    if intent.occasion:
        occ = OCCASIONS[intent.occasion]
        if p.style in occ["styles"]:
            score += 0.3 if p.style == occ["styles"][0] else 0.15
    if intent.season:
        if p.season == intent.season:
            score += 0.2
        elif {p.season, intent.season} == {"summer", "winter"}:
            score -= 0.4
    return score


def smart_search(query, limit=None, intent=None):
    intent = intent or parse(query)
    index = get_index()

    weights = expand(intent.keywords)
    if intent.occasion:
        for t in OCCASIONS[intent.occasion]["terms"]:
            weights[stem(t)] = weights.get(stem(t), 0) + 0.4
    qvec = index.query_vector(weights)

    has_structure = intent.categories or intent.colors or intent.occasion or intent.season
    # with only a budget/department filter ("under $50 for men") show everything that passes
    threshold = 0.05 if (intent.keywords or has_structure) else -99
    scored = []
    for p in index.products.values():
        if not passes_filters(p, intent):
            continue
        s = score_product(index, qvec, p, intent)
        if s > threshold:
            scored.append((p, round(s, 3)))
    scored.sort(key=lambda ps: (-ps[1], float(ps[0].price)))
    return SearchResult(query=query, intent=intent, results=scored[:limit] if limit else scored)
