import json

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .ai.pairing import complete_the_look
from .ai.search import smart_search
from .ai.sizing import recommend_size
from .ai.stylist import STARTERS, Stylist, serialise_look
from .currency import format_price
from .cart import Cart
from .forms import CheckoutForm, SignupForm
from .models import Category, Department, Order, OrderItem, Product
from .ratelimit import rate_limited
from .templatetags.store_extras import garment

STYLIST_SESSION_KEY = "stylist"


def home(request):
    products = Product.objects.select_related("category")
    hero = [products.filter(category__slug=slug, is_featured=True).first() for slug in ("coats", "dresses", "blazers")]
    return render(request, "store/home.html", {
        "hero": [p for p in hero if p],
        "dip_women": products.filter(department=Department.WOMEN, category__slug="coats").first(),
        "dip_men": products.filter(department=Department.MEN, category__slug="blazers").first(),
        # lead the editorial grid with a statement piece rather than, say, a belt
        "new_in": sorted(products.filter(is_new=True)[:12], key=lambda p: p.slot not in ("one_piece", "outerwear"))[:8],
        "featured_women": products.filter(is_featured=True, department=Department.WOMEN)[:4],
        "featured_men": products.filter(is_featured=True, department=Department.MEN)[:4],
        "starters": STARTERS,
        "ld": {
            "@context": "https://schema.org", "@type": "Organization", "name": settings.BRAND_NAME,
            "url": request.build_absolute_uri("/"),
            "address": {"@type": "PostalAddress", "addressLocality": "Paris", "addressCountry": "FR"},
        },
    })


def shop(request, department, category_slug=None):
    if department not in Department.values:
        raise Http404
    products = Product.objects.select_related("category").filter(department=department)
    category = None
    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=category)

    # a curated collection: presented in the house's order, no shopper-side filters
    categories = Category.objects.filter(products__department=department).distinct()
    return render(request, "store/shop.html", {
        "department": department,
        "department_label": Department(department).label,
        "category": category,
        "categories": categories,
        "products": products.order_by("category__sort_order", "-is_featured", "-price"),
    })


def product_detail(request, slug):
    product = get_object_or_404(Product.objects.select_related("category"), slug=slug)
    similar = (
        Product.objects.filter(department=product.department, category=product.category)
        .exclude(pk=product.pk)
        .select_related("category")[:4]
    )
    url = request.build_absolute_uri(product.get_absolute_url())
    dept_url = request.build_absolute_uri(f"/{product.department}/")
    ld = [
        {
            "@context": "https://schema.org", "@type": "Product", "name": product.name,
            "description": product.description, "material": product.material, "color": product.colors,
            "category": product.category.name, "sku": f"LA-{product.pk:05d}",
            "brand": {"@type": "Brand", "name": settings.BRAND_NAME},
            "offers": {"@type": "Offer", "price": f"{product.price:.2f}", "priceCurrency": "USD",
                       "availability": "https://schema.org/LimitedAvailability" if product.is_limited else "https://schema.org/InStock",
                       "url": url},
        },
        {
            "@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": product.get_department_display(), "item": dept_url},
                {"@type": "ListItem", "position": 2, "name": product.category.name,
                 "item": f"{dept_url}{product.category.slug}/"},
                {"@type": "ListItem", "position": 3, "name": product.name, "item": url},
            ],
        },
    ]
    return render(request, "store/product.html", {
        "ld": ld,
        "product": product,
        "look": complete_the_look(product),
        "similar": similar,
        "show_size_advisor": product.slot not in ("shoes", "accessory"),
    })


def search(request):
    q = request.GET.get("q", "").strip()
    result = smart_search(q) if q else None
    return render(request, "store/search.html", {"q": q, "result": result})


@rate_limited("search", per_minute=90)
def search_suggest(request):
    """Live search dropdown: top 5 AI matches as JSON."""
    q = request.GET.get("q", "").strip()
    if len(q) < 2:
        return JsonResponse({"results": [], "understood": []})
    result = smart_search(q, limit=5)
    return JsonResponse({
        "understood": result.intent.chips(),
        "results": [
            {"name": p.name, "url": p.get_absolute_url(), "price": format_price(p.price),
             "category": p.category.name, "art": str(garment(p, label=False))}
            for p in result.products
        ],
    })


# ---- AI stylist ------------------------------------------------------

def stylist(request):
    return render(request, "store/stylist.html", {"starters": STARTERS, "starters_json": json.dumps(STARTERS)})


@require_POST
@rate_limited("stylist")
def stylist_api(request):
    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    if payload.get("reset"):
        request.session.pop(STYLIST_SESSION_KEY, None)
        return JsonResponse({"ok": True})
    message = (payload.get("message") or "").strip()[:300]
    if not message:
        return JsonResponse({"error": "Say something first"}, status=400)

    bot = Stylist(request.session.get(STYLIST_SESSION_KEY))
    reply = bot.reply(message)
    request.session[STYLIST_SESSION_KEY] = reply["state"]
    return JsonResponse({
        "text": reply["text"],
        "look": serialise_look(reply["look"]),
        "understood": reply["understood"],
        "suggestions": reply["suggestions"],
    })


@require_POST
def size_api(request):
    try:
        payload = json.loads(request.body or "{}")
        product = Product.objects.get(pk=payload.get("product"))
        rec = recommend_size(payload["height"], payload["weight"], product.department, payload.get("fit", "regular"),
                             available=product.size_list)
    except (KeyError, ValueError, TypeError, json.JSONDecodeError, Product.DoesNotExist):
        return JsonResponse({"error": "Enter a height (cm) and weight (kg)."}, status=400)
    return JsonResponse(rec)


# ---- cart ------------------------------------------------------------

def _wants_json(request):
    return request.headers.get("x-requested-with") == "fetch"


def _quantity(raw):
    """Posted quantity as an int in 1..10; junk or negatives fall back to 1."""
    try:
        return max(1, min(int(raw), 10))
    except (TypeError, ValueError):
        return 1


def _limited_in_cart(cart, product):
    return any(k.split("|")[0] == str(product.id) for k in cart.data)


def cart_detail(request):
    return render(request, "store/cart.html", {"cart": Cart(request)})


@require_POST
def cart_add(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    size = request.POST.get("size") or product.size_list[0]
    color = request.POST.get("color") or (product.color_list[0] if product.color_list else "")
    if size not in product.size_list or (product.color_list and color not in product.color_list):
        if _wants_json(request):
            return JsonResponse({"error": "Pick a valid size and colour."}, status=400)
        messages.error(request, "Pick a valid size and colour.")
        return redirect(product)
    cart = Cart(request)
    if product.is_limited and _limited_in_cart(cart, product):
        msg = "This limited-edition piece is allocated one per client, and it is already in your bag."
        if _wants_json(request):
            resp = JsonResponse({"error": msg, "code": "LA-470"}, status=470)
            resp.reason_phrase = "Allocation Reached"
            return resp
        messages.error(request, f"{msg} (LA-470)")
        return redirect(product)
    cart.add(product, size, color, 1 if product.is_limited else _quantity(request.POST.get("quantity")))
    if _wants_json(request):
        return JsonResponse({"count": len(cart), "message": f"{product.name} added to your bag"})
    messages.success(request, f"{product.name} added to your bag.")
    return redirect(request.POST.get("next") or "cart")


@require_POST
def cart_add_look(request):
    """Add every piece of a stylist look at once, in the colour the stylist chose."""
    try:
        items = json.loads(request.body or "{}").get("items", [])
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    cart = Cart(request)
    products = Product.objects.in_bulk([i.get("id") for i in items])
    added = 0
    for i in items:
        p = products.get(i.get("id"))
        if not p or (p.is_limited and _limited_in_cart(cart, p)):
            continue
        color = i.get("color") if i.get("color") in p.color_list else (p.color_list[0] if p.color_list else "")
        size = "M" if "M" in p.size_list else p.size_list[len(p.size_list) // 2]
        cart.add(p, size, color)
        added += 1
    return JsonResponse({"count": len(cart), "message": f"Added {added} pieces to your bag"})


@require_POST
def cart_update(request):  # quantity <= 0 removes the line; Cart caps at 10
    cart = Cart(request)
    key = request.POST.get("key", "")
    if request.POST.get("action") == "remove":
        cart.remove(key)
    else:
        try:
            cart.set_quantity(key, int(request.POST.get("quantity", 1)))
        except ValueError:
            pass
    return redirect("cart")


# ---- checkout & accounts --------------------------------------------

def checkout(request):
    cart = Cart(request)
    if not len(cart):
        messages.info(request, "Your bag is empty.")
        return redirect("cart")
    initial = {}
    if request.user.is_authenticated:
        initial = {"full_name": request.user.get_full_name(), "email": request.user.email}
    form = CheckoutForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        order = form.save(commit=False)
        if request.user.is_authenticated:
            order.user = request.user
        order.save()
        OrderItem.objects.bulk_create([
            OrderItem(order=order, product=line["product"], size=line["size"], color=line["color"],
                      quantity=line["quantity"], price=line["price"])
            for line in cart
        ])
        cart.clear()
        request.session["last_order"] = order.pk
        return redirect("order_success", pk=order.pk)
    return render(request, "store/checkout.html", {"form": form, "cart": cart})


def order_success(request, pk):
    order = get_object_or_404(Order, pk=pk)
    owns = request.session.get("last_order") == order.pk or (request.user.is_authenticated and order.user_id == request.user.id)
    if not owns:
        raise Http404
    return render(request, "store/order_success.html", {"order": order})


def signup(request):
    form = SignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, f"Welcome to {settings.BRAND_NAME}, {user.username}.")
        return redirect("home")
    return render(request, "registration/signup.html", {"form": form})


@login_required
def account(request):
    orders = Order.objects.filter(Q(user=request.user)).prefetch_related("items__product")
    return render(request, "store/account.html", {"orders": orders})
