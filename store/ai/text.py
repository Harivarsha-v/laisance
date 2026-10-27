"""Tokenising and light normalisation shared by every AI feature."""

import re

from .lexicon import STOPWORDS, SYNONYMS

_WORD = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)?")


def stem(word):
    """Very light stemmer so 'shirts' and 'shirt' meet in the middle."""
    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"
    if word.endswith("es") and word[:-2].endswith(("sh", "ch", "x")):
        return word[:-2]
    if word.endswith("s") and not word.endswith("ss") and len(word) > 3:
        return word[:-1]
    return word


def words(text):
    """Lowercase words, hyphens kept ('t-shirt' -> 'tshirt'), no stemming."""
    text = (text or "").lower().replace("t-shirt", "tshirt").replace("off-white", "offwhite")
    return _WORD.findall(text)


def tokens(text):
    """Content tokens used for ranking: no stopwords, stemmed."""
    return [stem(w) for w in words(text) if w not in STOPWORDS and not w.isdigit()]


def expand(token_list):
    """Return {token: weight}: original tokens at 1.0 plus synonyms at 0.5."""
    weights = {}
    for t in token_list:
        weights[t] = weights.get(t, 0) + 1.0
        for syn in SYNONYMS.get(t, []):
            s = stem(syn)
            weights[s] = weights.get(s, 0) + 0.5
    return weights
