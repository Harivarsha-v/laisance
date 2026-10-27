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

Product and story photographs are from [Unsplash](https://unsplash.com) under the
[Unsplash License](https://unsplash.com/license) (free to use, no permission required). Only free-licence
images were used (no Unsplash+), and none show a recognisable brand logo. Files live in `static/img/`;
the mapping is in `store/photo_credits.py`. A photo uploaded in `/admin/` overrides the shipped one.

| Piece | Source |
|---|---|
| `suede-loafer-men` | https://unsplash.com/photos/a-pair-of-brown-suede-loafers-with-gold-hardwares-KOavcW0p7oc |
| `double-face-cashmere-overcoat-men` | https://unsplash.com/photos/man-in-brown-coat-and-black-pants-iIjResyhhW0 |
| `unstructured-linen-blazer-men` | https://unsplash.com/photos/a-pair-of-glasses-a-ball-of-yarn-a-pair-of-sunglasses-and-9Pspyy5lEMw |
| `cashmere-shawl-cardigan-men` | https://unsplash.com/photos/a-pair-of-sunglasses-and-a-sweater-on-a-white-surface-PbzOBFz8Ulc |
| `linen-camp-collar-shirt-men` | https://unsplash.com/photos/a-white-shirt-hanging-on-a-clothes-line-S4f4apZd-hA |
| `silk-cotton-knit-polo-men` | https://unsplash.com/photos/a-white-and-beige-shirt-with-a-black-collar-rhzkqvr4NH4 |
| `cashmere-jersey-tee-men` | https://unsplash.com/photos/a-white-shirt-on-a-white-background-4rUYuwJ2vGw |
| `suede-knee-high-boot-women` | https://unsplash.com/photos/a-pair-of-black-leather-slouch-boots-tDHBHyAO-Hw |
| `calfskin-ballerina-women` | https://unsplash.com/photos/a-pair-of-black-shoes-sitting-on-top-of-a-white-surface-UTXXzJA6O_E |
| `double-face-cashmere-long-coat-women` | https://unsplash.com/photos/woman-wearing-brown-single-breasted-coat-standing-in-front-of-gray-brick-wall-zkHv9pvrE9U |
| `double-breasted-wool-blazer-women` | https://unsplash.com/photos/young-woman-in-black-blazer-standing-against-a-white-wall-3_ZeD-2ITEs |
| `fluid-silk-wide-leg-trousers-women` | https://unsplash.com/photos/a-woman-poses-elegantly-on-a-wooden-stool-8FruAR7J1Ow |
| `double-face-cashmere-crewneck-women` | https://unsplash.com/photos/a-woman-wearing-a-beige-sweater-and-pants-rz3sw-8VNCw |
| `silk-crepe-de-chine-shirt-women` | https://unsplash.com/photos/a-woman-with-curly-hair-wearing-a-white-blouse-09iQ8pafMXU |
| `linen-voile-wrap-dress-women` | https://unsplash.com/photos/woman-in-white-tank-top-standing-on-sea-shore-during-daytime-CWKRCrBsgB4 |
| `silk-charmeuse-slip-dress-women` | https://unsplash.com/photos/woman-in-black-spaghetti-strap-dress-GNd5gstTSg8 |
| `wool-silk-suit-jacket-men` | https://unsplash.com/photos/man-in-blue-suit-standing-Ci_fZ5cL9Jo |
| `selvedge-denim-jeans-men` | https://unsplash.com/photos/a-pair-of-jeans-laying-on-a-tile-floor-jll9ZPrAVms |
| `pleated-wool-trousers-men` | https://unsplash.com/photos/a-man-in-a-suit-and-tie-walking-down-a-street-L3473EOotp4 |
| `merino-roll-neck-men` | https://unsplash.com/photos/man-in-black-suit-jacket-P43ZFLGgH38 |
| `cotton-poplin-shirt-men` | https://unsplash.com/photos/man-in-white-button-up-shirt-GDebkNryTd4 |
| `folded-calfskin-shoulder-bag-women` | https://unsplash.com/photos/a-black-bag-on-a-white-surface-o65-HVetXJ4 |
| `gabardine-trench-coat-women` | https://unsplash.com/photos/a-woman-in-a-trench-coat-standing-in-an-empty-building-9B5dtT0ROG4 |
| `wool-gabardine-tailored-trousers-women` | https://unsplash.com/photos/person-sitting-on-brown-wooden-chair-hLEfD4-8G4I |
| `cotton-poplin-boyfriend-shirt-women` | https://unsplash.com/photos/white-polo-shirt-hanged-on-brown-wooden-cabinet-ve2dwNxZ5Rg |
| `pleated-silk-crepe-gown-women` | https://unsplash.com/photos/woman-in-elegant-blue-dress-with-back-tattoo-oVnL3TRkzDg |
| `straw-panama-hat-men` | https://unsplash.com/photos/a-stylish-hat-rests-atop-a-wooden-form-1dPdmg6x448 |
| `canvas-and-leather-weekender-men` | https://unsplash.com/photos/brown-leather-duffel-bag-in-middle-on-gray-asphalt-road-PpzBE1hWeGI |
| `calfskin-belt-men` | https://unsplash.com/photos/a-close-up-of-a-belt-qTv4ePux4ck |
| `leather-low-top-sneaker-men` | https://unsplash.com/photos/pair-of-white-low-top-sneakers-IpSk8rGM64Q |
| `leather-court-sneaker-women` | https://unsplash.com/photos/pair-of-white-low-top-sneakers-IpSk8rGM64Q |
| `calfskin-derby-men` | https://unsplash.com/photos/a-pair-of-black-shoes-on-a-white-background-1iQUP9axQ_Y |
| `down-filled-wool-parka-men` | https://unsplash.com/photos/man-in-black-zip-up-jacket-and-blue-denim-jeans-standing-beside-gray-concrete-wall-during-uLWk3kDXBgU |
| `shearling-collar-suede-bomber-men` | https://unsplash.com/photos/man-in-brown-leather-jacket-wearing-black-sunglasses-bE6OvxczIc8 |
| `linen-bermuda-men` | https://unsplash.com/photos/a-row-of-white-pants-hanging-on-a-clothes-line-A8nR5I0dF2E |
| `linen-drawstring-trousers-men` | https://unsplash.com/photos/a-stylish-man-poses-with-folded-arms-9GqMLuNFWCw |
| `silk-evening-shirt-men` | https://unsplash.com/photos/a-man-wearing-a-suit-and-tie-KGwA-9S4lNo |
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
| `story/cloth` | https://unsplash.com/photos/pile-of-cloth-on-white-surface-4byBtNuIyIg |
| `story/leather` | https://unsplash.com/photos/a-leather-wallet-a-comb-thread-and-scissors-on-a-table-rhP8U-86GZA |
| `story/stitch` | https://unsplash.com/photos/hands-sewing-white-fabric-5ZQn_gWKvLE |
| `story/atelier` | https://unsplash.com/photos/a-room-filled-with-mannequins-and-sewing-machines-HIrP05jnXNs |
| `story/paris` | https://unsplash.com/photos/gray-landmark-building-UO02gAW3c0c |

## Scroll film (optional)

Put an MP4 at `static/video/atelier.mp4` and the home page story scrubs through it as you scroll
(otherwise the chapter photographs crossfade). For smooth scrubbing, encode with a keyframe on every frame and no audio:

```bash
ffmpeg -i flow_export.mp4 -an -vf "scale=1920:-2,fps=24" -c:v libx264 -preset slow -crf 22 -g 1 -pix_fmt yuv420p -movflags +faststart static/video/atelier.mp4
```
