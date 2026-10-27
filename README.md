# L’Aisance: a Paris maison with an AI stylist and client-care assistant

**Task title:** L’Aisance: luxury fashion house website with an integrated AI assistant for FAQs and error codes

**Live site:** https://laisance.onrender.com  <!-- replace with your Render URL after the first deploy -->
**Health check:** https://laisance.onrender.com/health/

A responsive Django website for a fictional high-end fashion house (relaxed, fluid tailoring and cashmere).
It has a curated seasonal collection, a private AI stylist, and an AI **client-care assistant** in a chat widget
on every page. The assistant answers from the FAQ database, explains error codes, and opens a support ticket
when it can't answer.

---

## How the assessment requirements are met

| Requirement | Where |
|---|---|
| Responsive site, 3+ pages, chat widget on every page | Home, Women/Men collection, product pages, Stylist, Client care (FAQ), Error codes, Contact, Bag, Checkout, Account, Health. The widget is in `templates/partials/assistant.html`, included by `base.html`. |
| 10+ FAQs stored in SQL, shown on the FAQ page | `FAQ` model, 15 entries loaded by `python manage.py seed_help`, shown at `/help/` |
| 8+ error codes (400, 401, 403, 404, 429, 500, 503 + site-specific) | `ErrorCode` model, shown at `/help/error-codes/`. Site-specific: **LA-470 Allocation reached** (limited-edition pieces are one per client; the bag returns HTTP 470). |
| Custom 404 and 500 pages with "Ask the assistant" | `templates/errors/error.html` via `handler404` / `handler500` (also 400, 403, CSRF, 429, 503). Each page opens the widget pre-filled with "What does error N mean?" |
| Assistant answers from FAQ data, explains error codes, creates a ticket when it can't answer | `store/ai/concierge.py` |
| Support tickets in SQL; chat logs and feedback in MongoDB | `SupportTicket` model (SQL). `store/mongo.py` writes `chat_logs` and `feedback` to MongoDB Atlas. |
| API keys and secrets in environment variables, nothing confidential in Git | `config/settings.py` reads everything from env vars, see `.env.example`. `.env` and the database are git-ignored. |
| Request logging | `store/middleware.py` `RequestLogMiddleware`: method, path, status, duration and IP for every request, to stdout and `logs/requests.log` |
| Health check page | `/health/` (HTML) and `/health.json`: SQL, MongoDB, exchange-rate API, request stats. Also Render's health check. |
| Third-party API with time limit and fallback | `store/currency.py`: Frankfurter exchange-rate API for the currency selector (USD, EUR, GBP, CHF, JPY). 2.5 s timeout, 6 h cache, then last good rates, then built-in reference rates. |

### Where each error code can actually happen
- **400:** malformed JSON sent to the assistant, stylist or feedback APIs.
- **401:** `/api/orders/` without signing in.
- **403:** expired CSRF token, or attaching an email to a ticket from another session.
- **404:** any unknown address.
- **429:** more than `AI_RATE_LIMIT` (20) assistant or stylist messages per minute.
- **500:** unhandled server error.
- **503:** `MAINTENANCE_MODE=true`.
- **LA-470:** adding a second limited-edition piece.

Every page can be previewed with its real status at `/help/error-codes/<code>/preview/`.

---

## The AI (runs in-house, no paid AI API)

All in `store/ai/`:
- **Client-care assistant** (`concierge.py`) checks, in order: greeting/thanks → asked for a person → **error code** (by number or description, e.g. "too many requests") → **FAQ** retrieval with TF-IDF vectors and cosine similarity, synonym expansion, a confidence threshold and keyword coverage → styling question (hands off to the stylist) → otherwise opens a **support ticket** and asks for the client's email. Each reply has "Was this helpful?" feedback.
- **Stylist** (`stylist.py`): conversational outfit builder (occasion, budget, colours, department and season, with follow-ups like "a lighter budget", "another look", "in black").
- **Smart search** (`search.py`), **Complete the look** (`pairing.py`), **copywriter** (`copywriter.py`, writes product descriptions) and **size advisor** (`sizing.py`).

---

## Run locally

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then set DEBUG=true and a SECRET_KEY; MONGODB_URI is optional locally
python manage.py migrate
python manage.py seed_store   # the collection
python manage.py seed_help    # FAQs + error codes
python manage.py createsuperuser
python manage.py runserver 8002
```

Without `MONGODB_URI`, chat logs and feedback go to `logs/*.jsonl` and `/health/` shows MongoDB as "fallback".

## Deploy (Render + MongoDB Atlas)

1. **MongoDB Atlas:** create a free M0 cluster, a database user, and allow access from anywhere (`0.0.0.0/0`). Copy the `mongodb+srv://…` connection string.
2. **Render:** New → Blueprint → pick this GitHub repo. `render.yaml` creates the web service (HTTPS) and a Postgres database, and generates `SECRET_KEY`.
3. When asked, paste the Atlas string as **`MONGODB_URI`**.
4. After the first deploy, open `/health/`. Everything should read Operational. Put the URL at the top of this README.
5. Admin: in the Render shell run `python manage.py createsuperuser`, then sign in at `/admin/` to see tickets, FAQs and orders.

Environment variables: `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `DATABASE_URL`, `MONGODB_URI`,
`MONGODB_DB`, `CURRENCY_API_URL`, `CURRENCY_API_KEY` (optional), `CURRENCY_API_TIMEOUT`, `AI_RATE_LIMIT`, `MAINTENANCE_MODE`.

## Checks before submitting
- [ ] Open the live link on a phone: menu, chat widget, product page, FAQ.
- [ ] Visit `https://<site>/this-does-not-exist`: the custom 404 appears, and "Ask the assistant" explains it.
- [ ] Ask the widget something it can't know ("do you sponsor football teams?"): a ticket `LA-000xx` is created (visible in `/admin/`).
- [ ] `/health/` shows SQL, MongoDB and the exchange-rate API as Operational.

---

## Proposed improvement

**Learn from unanswered questions.** Every ticket the assistant opens, and every "not helpful" vote in MongoDB, marks a gap in the FAQs. A staff dashboard could cluster those messages (using the same TF-IDF vectors), show the most common unanswered themes each week, and let an advisor turn one into a new FAQ with one click. The assistant would then improve from real client questions. A further step would be to swap TF-IDF for sentence embeddings, so "my parcel hasn't arrived" matches "How can I track my order?" even with no shared words.

---

## Project layout

```
config/                 settings (env-driven), urls, error handlers
store/
  ai/                   concierge (assistant), stylist, search, pairing, copywriter, sizing, lexicon
  models.py             Product, Category, Order, FAQ, ErrorCode, SupportTicket
  views.py              shop, product, bag, checkout, stylist API
  views_care.py         FAQ, error codes, contact, assistant APIs, error pages, health check
  middleware.py         request logging, maintenance mode (503), currency
  mongo.py              MongoDB chat logs + feedback (with file fallback)
  currency.py           exchange-rate API with timeout + fallback
  ratelimit.py          429 rate limiting for the AI endpoints
  management/commands/  seed_store, seed_help
templates/              pages, partials (assistant widget), errors
static/                 css, js
render.yaml, build.sh   deployment
```

*A student project. No payments are taken and the brand is fictional.*


## Photography credits

Product photographs are from [Unsplash](https://unsplash.com) under the
[Unsplash License](https://unsplash.com/license) (free to use, no permission required). Only free-licence
images were used (no Unsplash+), and none show a recognisable brand logo. Files live in `static/img/`;
the mapping is in `store/photo_credits.py`. A photo uploaded in `/admin/` overrides the shipped one.

| Piece | Source |
|---|---|
| `suede-loafer-men` | https://unsplash.com/photos/a-pair-of-brown-leather-loafers-on-a-stool-xPpfEQe0ZiY |
| `double-face-cashmere-overcoat-men` | https://unsplash.com/photos/a-person-in-a-suit-A5nuQ2Lvg40 |
| `unstructured-linen-blazer-men` | https://unsplash.com/photos/a-man-touching-his-suit-jacket-J0FuYqNWviw |
| `cashmere-shawl-cardigan-men` | https://unsplash.com/photos/man-wearing-a-cap-glasses-and-scarf-outdoors-Lkc5ruvG-v0 |
| `linen-camp-collar-shirt-men` | https://unsplash.com/photos/man-walking-on-a-wooden-deck-by-the-ocean-kXsBsAp5Q0Y |
| `silk-cotton-knit-polo-men` | https://unsplash.com/photos/white-polo-shirt-on-black-table-SL2g8Ry_Ozs |
| `cashmere-jersey-tee-men` | https://unsplash.com/photos/white-crew-neck-t-shirt-acn5ERAeSb4 |
| `suede-knee-high-boot-women` | https://unsplash.com/photos/a-pair-of-black-leather-slouch-boots-tDHBHyAO-Hw |
| `calfskin-ballerina-women` | https://unsplash.com/photos/a-pair-of-black-shoes-sitting-on-top-of-a-white-surface-UTXXzJA6O_E |
| `double-face-cashmere-long-coat-women` | https://unsplash.com/photos/woman-in-brown-coat-and-gray-pants-standing-on-white-concrete-staircase-DsKcWDk6NEU |
| `double-breasted-wool-blazer-women` | https://unsplash.com/photos/young-woman-with-flowing-blonde-hair-wearing-a-beige-suit-h8fJcfaARJg |
| `fluid-silk-wide-leg-trousers-women` | https://unsplash.com/photos/a-woman-poses-elegantly-on-a-wooden-stool-8FruAR7J1Ow |
| `double-face-cashmere-crewneck-women` | https://unsplash.com/photos/woman-in-gray-sweater-standing-on-brown-field-during-daytime-f5R8nfQzPq8 |
| `silk-crepe-de-chine-shirt-women` | https://unsplash.com/photos/a-woman-with-curly-hair-wearing-a-white-blouse-09iQ8pafMXU |
| `linen-voile-wrap-dress-women` | https://unsplash.com/photos/young-woman-in-white-dress-leaning-against-wooden-wall-ZTO2YSqlxnM |
| `silk-charmeuse-slip-dress-women` | https://unsplash.com/photos/woman-in-black-spaghetti-strap-dress-nh3SsL7_BNw |
| `wool-silk-suit-jacket-men` | https://unsplash.com/photos/a-man-in-a-suit-sitting-in-a-chair-HPNHsdzZKR8 |
| `selvedge-denim-jeans-men` | https://unsplash.com/photos/person-in-leather-jacket-and-jeans-g9nI32Nuj6I |
| `pleated-wool-trousers-men` | https://unsplash.com/photos/man-walking-on-cobblestone-street-02e96bYh4q8 |
| `merino-roll-neck-men` | https://unsplash.com/photos/man-in-beige-blazer-and-turtleneck-n_2BpUTKZzM |
| `cotton-poplin-shirt-men` | https://unsplash.com/photos/a-couple-stands-on-a-balcony-with-lush-foliage-eXBlGNmCW-Q |
| `folded-calfskin-shoulder-bag-women` | https://unsplash.com/photos/a-black-bag-on-a-white-surface-o65-HVetXJ4 |
| `gabardine-trench-coat-women` | https://unsplash.com/photos/a-woman-in-a-trench-coat-standing-in-an-empty-building-9B5dtT0ROG4 |
| `wool-gabardine-tailored-trousers-women` | https://unsplash.com/photos/person-sitting-on-brown-wooden-chair-hLEfD4-8G4I |
| `cotton-poplin-boyfriend-shirt-women` | https://unsplash.com/photos/white-polo-shirt-hanged-on-brown-wooden-cabinet-ve2dwNxZ5Rg |
| `pleated-silk-crepe-gown-women` | https://unsplash.com/photos/woman-in-elegant-blue-dress-with-back-tattoo-oVnL3TRkzDg |
| `straw-panama-hat-men` | https://unsplash.com/photos/shallow-focus-photo-of-person-in-black-sleeveless-shirt-near-body-of-water-4S0imhdB7Uo |
| `canvas-and-leather-weekender-men` | https://unsplash.com/photos/person-holding-brown-leather-handbag-lFvkXTEYS4s |
| `calfskin-belt-men` | https://unsplash.com/photos/a-pair-of-brown-leather-belts-sitting-on-top-of-a-white-piece-of-paper-rH16wMV8ImM |
| `leather-low-top-sneaker-men` | https://unsplash.com/photos/person-holding-white-nike-low-top-sneakers-PUw24-taMKc |
| `leather-court-sneaker-women` | https://unsplash.com/photos/pair-of-white-low-top-sneakers-IpSk8rGM64Q |
| `calfskin-derby-men` | https://unsplash.com/photos/mens-black-dress-shoes-cologne-and-bow-tie-TjrW-yHmL6o |
| `down-filled-wool-parka-men` | https://unsplash.com/photos/woman-hands-on-jackets-pocket-Jr_cb6kPUxM |
| `shearling-collar-suede-bomber-men` | https://unsplash.com/photos/a-close-up-of-a-jacket-with-a-label-on-it-6dejojG4QEQ |
| `linen-bermuda-men` | https://unsplash.com/photos/a-couple-of-men-standing-next-to-each-other-kSAsxxY-HwE |
| `linen-drawstring-trousers-men` | https://unsplash.com/photos/a-man-standing-in-a-doorway-with-his-hands-in-his-pockets-Xhvbh9d4bho |
| `silk-evening-shirt-men` | https://unsplash.com/photos/man-in-white-shirt-with-jacket-draped-over-shoulders-89buga-M110 |
| `silk-twill-scarf-90-women` | https://unsplash.com/photos/a-scrunchie-with-an-avocado-and-orange-slice-6Slg2fOeaQ0 |
| `woven-raffia-tote-women` | https://unsplash.com/photos/a-basket-with-a-plant-in-it-Ak7lAuarT1I |
| `leather-strappy-sandal-women` | https://unsplash.com/photos/black-patent-leather-high-heel-sandals-aTNcFxR3M10 |
| `lambskin-biker-jacket-women` | https://unsplash.com/photos/black-leather-zip-up-jacket-on-white-textile-nsRBbE6-YLs |
| `linen-bermuda-shorts-women` | https://unsplash.com/photos/a-person-in-a-white-dress-xGr1QMjiWcg |
| `bias-cut-satin-skirt-women` | https://unsplash.com/photos/a-woman-poses-elegantly-against-wood-Q0aTeTa9qNM |
| `raw-selvedge-straight-jeans-women` | https://unsplash.com/photos/woman-in-white-tank-top-and-blue-denim-jeans-sitting-on-white-chair-2s3GhhJz2uY |
| `cable-knit-cashmere-cardigan-women` | https://unsplash.com/photos/woman-in-white-cardigan-sitting-on-beach-during-daytime-pJ3DtntO-LQ |
| `featherweight-cashmere-tee-women` | https://unsplash.com/photos/a-woman-posing-for-a-picture-with-her-hands-on-her-hips-_k_uEf2xVF0 |
| `cashmere-rib-column-dress-women` | https://unsplash.com/photos/a-woman-in-a-dress-JErC76g3ZFU |

The home-page story frames (`static/img/story/`) are the owner's own keyframes, generated in Google Flow.

## Scroll film (optional)

Put an MP4 at `static/video/atelier.mp4` and the home page story scrubs through it as you scroll
(otherwise the chapter photographs crossfade). For smooth scrubbing, encode with a keyframe on every frame and no audio:

```bash
ffmpeg -i flow_export.mp4 -an -vf "scale=1920:-2,fps=24" -c:v libx264 -preset slow -crf 22 -g 1 -pix_fmt yuv420p -movflags +faststart static/video/atelier.mp4
```
