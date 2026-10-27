from django.core.management.base import BaseCommand
from django.db import transaction

from store.models import Category, OrderItem, Product

CATEGORIES = [
    ("Dresses", "dresses", "one_piece"),
    ("Tops & T-Shirts", "t-shirts", "top"),
    ("Shirts", "shirts", "top"),
    ("Knitwear", "knitwear", "top"),
    ("Trousers", "trousers", "bottom"),
    ("Denim", "jeans", "bottom"),
    ("Skirts", "skirts", "bottom"),
    ("Shorts", "shorts", "bottom"),
    ("Tailoring", "blazers", "outerwear"),
    ("Coats & Jackets", "coats", "outerwear"),
    ("Shoes", "shoes", "shoes"),
    ("Leather Goods & Accessories", "accessories", "accessory"),
]

SWATCHES = {
    "black": "#1f1e1c", "white": "#f3f1ec", "ecru": "#e8e0cf", "beige": "#d6c7ad", "camel": "#b48a5e",
    "brown": "#6a4b35", "grey": "#9b9a96", "navy": "#25324a", "blue": "#7491b4", "green": "#6e7558",
    "red": "#7b2832", "pink": "#e3b9b6", "yellow": "#e6d07c", "champagne": "#e4d3b4",
}

W_SHOES = "36, 37, 38, 39, 40, 41"
M_SHOES = "40, 41, 42, 43, 44, 45"
ONE = "One size"

# A deliberately small, seasonal collection.
# name, department, category, price, material, colours, style, season, new, featured, limited, sizes
PRODUCTS = [
    # ---- women
    ("Silk Charmeuse Slip Dress", "women", "dresses", 4850, "Silk charmeuse, woven in Lyon", "black, champagne", "evening", "all", True, True, False, None),
    ("Linen Voile Wrap Dress", "women", "dresses", 3650, "Linen voile from Normandy", "ecru, beige", "casual", "summer", True, True, False, None),
    ("Pleated Silk Crêpe Gown", "women", "dresses", 8900, "Silk crêpe, hand-pleated", "navy, red", "formal", "all", False, True, True, None),
    ("Cashmere Rib Column Dress", "women", "dresses", 4200, "Pure cashmere rib", "grey, brown", "casual", "transitional", False, False, False, None),
    ("Featherweight Cashmere Tee", "women", "t-shirts", 890, "Cashmere jersey", "ecru, black", "casual", "all", False, False, False, None),
    ("Silk Crêpe de Chine Shirt", "women", "shirts", 1650, "Silk crêpe de chine", "ecru, black, pink", "evening", "all", True, False, False, None),
    ("Cotton Poplin Boyfriend Shirt", "women", "shirts", 1150, "Egyptian cotton poplin", "white, blue", "work", "all", False, True, False, None),
    ("Double-Face Cashmere Crewneck", "women", "knitwear", 2450, "Double-face cashmere", "camel, grey, ecru", "casual", "winter", True, True, False, None),
    ("Cable-Knit Cashmere Cardigan", "women", "knitwear", 2900, "Hand-framed cashmere", "ecru, green", "casual", "transitional", False, False, False, None),
    ("Wool Gabardine Tailored Trousers", "women", "trousers", 1450, "Wool gabardine from Biella", "black, beige, grey", "work", "all", False, True, False, None),
    ("Fluid Silk Wide-Leg Trousers", "women", "trousers", 1890, "Heavy silk crêpe", "ecru, black", "evening", "summer", True, False, False, None),
    ("Raw Selvedge Straight Jeans", "women", "jeans", 1050, "Japanese selvedge denim", "blue, black", "casual", "all", False, False, False, None),
    ("Bias-Cut Satin Skirt", "women", "skirts", 1750, "Silk satin, cut on the bias", "champagne, black, green", "evening", "all", False, False, False, None),
    ("Linen Bermuda Shorts", "women", "shorts", 980, "Washed Normandy linen", "beige, white", "casual", "summer", False, False, False, None),
    ("Double-Breasted Wool Blazer", "women", "blazers", 4450, "Wool and silk suiting", "black, beige, navy", "work", "all", True, True, False, None),
    ("Double-Face Cashmere Long Coat", "women", "coats", 8600, "Double-face cashmere, hand-finished", "camel, black", "work", "winter", True, True, True, None),
    ("Gabardine Trench Coat", "women", "coats", 5900, "Cotton gabardine", "beige, navy", "casual", "transitional", False, True, False, None),
    ("Lambskin Biker Jacket", "women", "coats", 7200, "Nappa lambskin", "black, brown", "street", "transitional", False, False, True, None),
    ("Leather Strappy Sandal", "women", "shoes", 1150, "Calfskin, leather sole", "black, beige", "evening", "summer", False, False, False, W_SHOES),
    ("Calfskin Ballerina", "women", "shoes", 980, "Box calfskin", "black, red", "work", "all", True, False, False, W_SHOES),
    ("Leather Court Sneaker", "women", "shoes", 950, "Calfskin", "white, beige", "casual", "all", False, False, False, W_SHOES),
    ("Suede Knee-High Boot", "women", "shoes", 2350, "Goat suede", "black, brown", "evening", "winter", True, False, False, W_SHOES),
    ("Folded Calfskin Shoulder Bag", "women", "accessories", 7800, "Box calfskin, saddle-stitched", "black, ecru", "evening", "all", False, True, True, ONE),
    ("Woven Raffia Tote", "women", "accessories", 2650, "Hand-woven raffia, calfskin trim", "beige", "casual", "summer", False, False, False, ONE),
    ("Silk Twill Scarf 90", "women", "accessories", 680, "Silk twill, hand-rolled edges", "camel, navy", "casual", "all", False, False, False, ONE),
    # ---- men
    ("Cashmere Jersey Tee", "men", "t-shirts", 790, "Cashmere jersey", "white, black, grey", "casual", "all", True, False, False, None),
    ("Silk-Cotton Knit Polo", "men", "t-shirts", 1350, "Silk and cotton knit", "ecru, navy, brown", "casual", "summer", True, True, False, None),
    ("Cotton Poplin Shirt", "men", "shirts", 1050, "Egyptian cotton poplin", "white, blue", "work", "all", False, True, False, None),
    ("Linen Camp-Collar Shirt", "men", "shirts", 1150, "Normandy linen", "ecru, green, blue", "casual", "summer", True, False, False, None),
    ("Silk Evening Shirt", "men", "shirts", 1750, "Silk satin", "black, navy", "evening", "all", False, False, False, None),
    ("Merino Roll Neck", "men", "knitwear", 1450, "Extra-fine merino", "black, camel, grey", "work", "winter", False, True, False, None),
    ("Cashmere Shawl Cardigan", "men", "knitwear", 3200, "Chunky cashmere", "ecru, brown", "casual", "winter", True, False, False, None),
    ("Pleated Wool Trousers", "men", "trousers", 1350, "Wool flannel from Biella", "grey, black, navy", "work", "all", False, True, False, None),
    ("Linen Drawstring Trousers", "men", "trousers", 1150, "Washed Normandy linen", "beige, white", "casual", "summer", False, False, False, None),
    ("Selvedge Denim Jeans", "men", "jeans", 990, "Japanese selvedge denim", "blue, black", "casual", "all", False, True, False, None),
    ("Linen Bermuda", "men", "shorts", 850, "Washed Normandy linen", "beige, navy", "casual", "summer", False, False, False, None),
    ("Wool-Silk Suit Jacket", "men", "blazers", 5400, "Wool and silk suiting", "navy, black, grey", "formal", "all", False, True, False, None),
    ("Unstructured Linen Blazer", "men", "blazers", 3900, "Linen and silk", "beige, navy", "casual", "summer", True, False, False, None),
    ("Double-Face Cashmere Overcoat", "men", "coats", 8900, "Double-face cashmere, hand-finished", "camel, black, grey", "work", "winter", True, True, True, None),
    ("Shearling-Collar Suede Bomber", "men", "coats", 6800, "Goat suede, shearling collar", "brown, black", "street", "transitional", False, False, True, None),
    ("Down-Filled Wool Parka", "men", "coats", 5200, "Technical wool, goose down", "black, green", "street", "winter", False, False, False, None),
    ("Calfskin Derby", "men", "shoes", 1450, "Box calfskin, Goodyear-welted", "black, brown", "formal", "all", False, False, False, M_SHOES),
    ("Suede Loafer", "men", "shoes", 1250, "Calf suede", "brown, navy", "casual", "all", True, False, False, M_SHOES),
    ("Leather Low-Top Sneaker", "men", "shoes", 950, "Calfskin", "white, black", "casual", "all", False, True, False, M_SHOES),
    ("Calfskin Belt", "men", "accessories", 650, "Box calfskin, palladium buckle", "black, brown", "work", "all", False, False, False, ONE),
    ("Canvas and Leather Weekender", "men", "accessories", 6900, "Cotton canvas, calfskin", "beige, navy", "casual", "all", False, False, False, ONE),
    ("Straw Panama Hat", "men", "accessories", 850, "Hand-woven toquilla straw", "beige", "casual", "summer", False, False, False, ONE),
]


class Command(BaseCommand):
    help = "Load categories and the seasonal collection. Use --reset to replace existing products."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true")

    @transaction.atomic
    def handle(self, *args, reset=False, **opts):
        if reset:
            OrderItem.objects.all().delete()
            Product.objects.all().delete()
        cats = {}
        for i, (name, slug, slot) in enumerate(CATEGORIES):
            cats[slug], _ = Category.objects.update_or_create(slug=slug, defaults={"name": name, "slot": slot, "sort_order": i})

        created = 0
        for name, dept, cat, price, material, colors, style, season, new, featured, limited, sizes in PRODUCTS:
            first = colors.split(",")[0].strip()
            _, was_created = Product.objects.get_or_create(
                name=name,
                department=dept,
                defaults=dict(
                    category=cats[cat], price=price, material=material, colors=colors, style=style,
                    season=season, is_new=new, is_featured=featured, is_limited=limited,
                    sizes=sizes or "XS, S, M, L, XL", swatch=SWATCHES.get(first, "#d9d4cc"),
                ),
            )
            created += was_created
        self.stdout.write(self.style.SUCCESS(f"{len(cats)} categories, {created} new pieces (AI wrote their copy)."))
