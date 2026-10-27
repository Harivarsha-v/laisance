"""The client-care assistant (the chat widget on every page).

It answers only from what the maison has written down:
  1. error codes        -> the ErrorCode table ("what does 429 mean?", "page not found")
  2. frequent questions -> the FAQ table, matched with TF-IDF retrieval + synonyms
  3. styling requests   -> handed to the AI stylist
  4. anything else      -> a SupportTicket is opened in SQL so a person can reply
"""

import math
import re
from collections import Counter

from django.urls import reverse
from django.utils.html import escape

from ..models import FAQ, ErrorCode, SupportTicket
from .intent import parse
from .text import expand, tokens, words

CODE_RE = re.compile(r"\b(?:(la)[-\s]?)?([45]\d\d)\b", re.I)
# plain-language descriptions of errors -> code
ERROR_PHRASES = [
    (r"not found|page (?:doesn'?t|does not) exist|broken link|dead link|missing page", "404"),
    (r"too many requests|rate.?limit|slow down|paused", "429"),
    (r"forbidden|access (?:denied|refused)|not allowed|permission|csrf", "403"),
    (r"unauthori[sz]ed|not (?:logged|signed) in|need to (?:log|sign) in|sign.?in required", "401"),
    (r"bad request|malformed|invalid request", "400"),
    (r"server error|internal error|something went wrong|crash", "500"),
    (r"unavailable|maintenance|down for|site (?:is )?down|offline", "503"),
    (r"allocation|one per client|only one|limited edition.*(?:second|two|another|more)", "LA-470"),
]
ERROR_CONTEXT = re.compile(r"\b(error|code|status|mean|means|meaning|got|getting|see|seeing|shows?|showing|page)\b", re.I)
HUMAN_RE = re.compile(r"\b(human|person|someone|agent|advisor|adviser|representative|call me|speak to|talk to|real person|complaint)\b", re.I)
TICKET_RE = re.compile(r"\b(support request|open a (?:ticket|request)|raise a ticket|create a ticket|ticket)\b", re.I)
ALL_CODES_RE = re.compile(r"\b(all|list|which|every)\b.*\berror codes?\b|\berror codes? (?:page|list)\b", re.I)
GREETING = {"hi", "hello", "hey", "bonjour", "hiya"}
THANKS = {"thanks", "thank", "merci", "cheers", "perfect", "great", "helpful"}

FAQ_THRESHOLD = 0.22
MIN_COVERAGE = 0.5  # at least half the question's content words must appear somewhere in the FAQs
# question words carry no topic, so they shouldn't make two questions look alike
QUESTION_WORDS = {"do", "doe", "does", "how", "can", "could", "what", "when", "where", "why", "who", "which", "will",
                  "should", "would", "may", "might", "is", "are", "am", "there", "yes", "much", "many", "us", "our", "we"}


def faq_tokens(text):
    return [t for t in tokens(text) if t not in QUESTION_WORDS]
STARTERS = ["How long does delivery take?", "What is your returns policy?", "What does error 429 mean?", "Speak to an advisor"]


class FaqIndex:
    """TF-IDF vectors over the FAQ table (question weighted x3, keywords x2, answer x1)."""

    def __init__(self, faqs):
        self.faqs = list(faqs)
        # words an editor explicitly attached to an answer: a strong signal even in a long question
        self.keyword_vocab = {t for f in self.faqs for t in faq_tokens(f.keywords)}
        docs = []
        for f in self.faqs:
            terms = Counter()
            for t in faq_tokens(f.question):
                terms[t] += 3
            for t in faq_tokens(f.keywords):
                terms[t] += 2
            for t in faq_tokens(f.answer):
                terms[t] += 1
            docs.append(terms)
        n = len(docs) or 1
        df = Counter(t for d in docs for t in d)
        self.idf = {t: math.log((n + 1) / (c + 1)) + 1 for t, c in df.items()}
        self.vectors = [self._norm({t: tf * self.idf[t] for t, tf in d.items()}) for d in docs]

    @staticmethod
    def _norm(v):
        n = math.sqrt(sum(x * x for x in v.values())) or 1.0
        return {t: x / n for t, x in v.items()}

    def coverage(self, text):
        words_ = faq_tokens(text)
        return sum(t in self.idf for t in words_) / len(words_) if words_ else 0.0

    def confident(self, text, score):
        if score >= FAQ_THRESHOLD and self.coverage(text) >= MIN_COVERAGE:
            return True
        return score >= FAQ_THRESHOLD / 2 and bool(set(faq_tokens(text)) & self.keyword_vocab)

    def search(self, text, k=3):
        q = self._norm({t: w * self.idf[t] for t, w in expand(faq_tokens(text)).items() if t in self.idf})
        if not q:
            return []
        scored = [(sum(w * vec.get(t, 0) for t, w in q.items()), f) for vec, f in zip(self.vectors, self.faqs)]
        return sorted([s for s in scored if s[0] > 0], key=lambda s: -s[0])[:k]


def find_error_code(message):
    """Return an error code string mentioned or described in the message, if any."""
    for m in CODE_RE.finditer(message):
        prefix, num = m.group(1), m.group(2)
        code = f"LA-{num}" if prefix or num == "470" else num
        # a bare number only counts as an error code when the message is about errors ("$400" is a price)
        if prefix or ERROR_CONTEXT.search(message) or message.strip().strip("?").isdigit():
            if message[max(0, m.start() - 1):m.start()] != "$":
                return code
    low = message.lower()
    if ERROR_CONTEXT.search(low) or len(low.split()) <= 6:
        for pattern, code in ERROR_PHRASES:
            if re.search(pattern, low):
                return code
    return None


def _p(text):
    return f"<p>{text}</p>"


class Concierge:
    def __init__(self, page=""):
        self.page = page[:255]

    def reply(self, message):
        message = (message or "").strip()
        ws = set(words(message))
        if ws & GREETING and len(ws) <= 4:
            return self._r("greeting", _p("Bonjour, and welcome to the maison. I can help with orders, delivery, returns, "
                                          "our pieces and services, or explain any error code you see. How may I help?"),
                           suggestions=STARTERS)
        if ws & THANKS and len(ws) <= 5:
            return self._r("thanks", _p("It is a pleasure. Is there anything else I can do for you?"), suggestions=STARTERS[:2])

        if HUMAN_RE.search(message):
            return self._ticket(message, "Of course. I've passed your request to our client advisors")
        if TICKET_RE.search(message):
            return self._ticket(message, "Certainly")
        if ALL_CODES_RE.search(message):
            codes = ", ".join(ErrorCode.objects.values_list("code", flat=True))
            return self._r("info", _p(f"The codes you may meet on our site are {codes}. Each is explained on our "
                                      f"<a href=\"{reverse('error_codes')}\">error codes page</a>, or ask me about any one of them."),
                           matched="error:list", suggestions=["What does 403 mean?", "What is LA-470?"])

        code = find_error_code(message)
        if code:
            return self._error(code)

        index = FaqIndex(FAQ.objects.filter(is_published=True))
        hits = index.search(message)
        if hits and index.confident(message, hits[0][0]):
            score, faq = hits[0]
            related = [f.question for s, f in hits[1:] if s >= FAQ_THRESHOLD * 0.6]
            return self._r("faq", _p(escape(faq.answer)), matched=f"faq:{faq.pk}", title=faq.question,
                           confidence=round(min(score, 1), 2), suggestions=related or STARTERS[:2])

        intent = parse(message)
        if intent.occasion or intent.categories:
            url = f"{reverse('stylist')}?q={escape(message)}"
            return self._r("stylist", _p("That is a question for our stylist, who can compose a complete look from the "
                                         f"collection. <a href=\"{url}\">Continue with the stylist →</a>"),
                           matched="stylist")

        return self._ticket(message, "I'm not certain I can answer that properly")

    # ---- branches -----------------------------------------------------
    def _error(self, code):
        err = ErrorCode.objects.filter(code__iexact=code).first()
        if not err:
            known = ", ".join(ErrorCode.objects.values_list("code", flat=True))
            return self._r("error", _p(f"Error {escape(code)} isn't one our site uses. The codes you may see are {known}. "
                                       "Tell me which one appeared and I'll explain it."), matched=f"error:{code}")
        html = (f"<p><strong>{escape(err.code)} · {escape(err.title)}.</strong> {escape(err.meaning)}</p>"
                f"<p><em>What to do:</em> {escape(err.what_to_do)}</p>")
        return self._r("error", html, matched=f"error:{err.code}", title=f"Error {err.code}",
                       suggestions=["Open a support request", "See all error codes"])

    def _ticket(self, message, opening):
        ticket = SupportTicket.objects.create(
            subject=message[:150] or "Assistance requested", message=message or "(no message)",
            source=SupportTicket.Source.ASSISTANT, page=self.page,
        )
        html = _p(f"{opening}, so I've opened request <strong>{ticket.reference}</strong> for our client care team. "
                  "Leave your email below and an advisor will reply within one working day.")
        return self._r("ticket", html, matched=f"ticket:{ticket.pk}", ticket=ticket.reference)

    def _r(self, kind, html, matched="", title="", confidence=None, suggestions=None, ticket=""):
        return {"kind": kind, "html": html, "matched": matched, "title": title, "confidence": confidence,
                "suggestions": suggestions or [], "ticket": ticket}
