"""Template helpers, including the illustrated garment artwork used until real photos are uploaded."""

from django import template
from django.utils.html import format_html
from django.utils.safestring import mark_safe

register = template.Library()

def _ink_for(hex_color):
    """Readable text colour on top of a given swatch (used by the product page colour picker)."""
    try:
        h = hex_color.lstrip("#")
        r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    except (ValueError, AttributeError):
        return "#1d1b18"
    return "#1d1b18" if 0.2126 * r + 0.7152 * g + 0.0722 * b > 140 else "#f4efe6"


@register.simple_tag
def garment(product, css_class="", label=True, color=None):
    """Product artwork: the uploaded photo if there is one, otherwise a rendered flat-lay in the chosen colour.
    label=True adds a catalogue caption (material and plate number), shown on large images only."""
    from ..artwork import backdrop_for, flat_lay_svg

    if product.image:
        return format_html(
            '<figure class="art {}"><img src="{}" alt="{}" loading="lazy"></figure>',
            css_class, product.image.url, product.name,
        )
    swatch = COLOR_HEX.get((color or "").lower(), product.swatch)
    caption = (
        format_html('<figcaption><span>{}</span><span>Pl. {}</span></figcaption>', product.material, f"{product.pk:03d}")
        if label else ""
    )
    return format_html(
        '<figure class="art art--drawn {cls}" style="--sweep:{bg}" data-swatch="{sw}" role="img" aria-label="{name}">{svg}{caption}</figure>',
        cls=css_class, bg=backdrop_for(swatch), sw=swatch, name=product.name, caption=caption,
        svg=mark_safe(flat_lay_svg(product, swatch)),  # noqa: S308 - built from constants and validated hex colours
    )


@register.filter
def ld_json(data):
    """Render a dict as a JSON-LD <script> block. '<', '>' and '&' are escaped so data can't close the tag."""
    import json

    payload = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    return mark_safe(f'<script type="application/ld+json">{payload}</script>')  # noqa: S308 - escaped above


@register.simple_tag(takes_context=True)
def absolute(context, path):
    return context["request"].build_absolute_uri(path)


@register.filter
def money(value):
    """Price in the client's chosen currency (rates from the exchange-rate API, with fallback)."""
    from ..currency import format_price

    try:
        return format_price(value)
    except (TypeError, ValueError):
        return value


COLOR_HEX = {
    "black": "#1f1e1c", "white": "#f6f4ef", "ecru": "#e8e0cf", "beige": "#d6c7ad", "camel": "#b48a5e",
    "brown": "#6a4b35", "grey": "#9b9a96", "navy": "#25324a", "blue": "#7491b4", "green": "#6e7558",
    "red": "#7b2832", "pink": "#e3b9b6", "yellow": "#e6d07c", "champagne": "#e4d3b4", "gold": "#c9a85a",
}


@register.filter
def color_hex(name):
    return COLOR_HEX.get((name or "").lower(), "#ccc")


@register.filter
def ink_for(name):
    """Line colour that reads on a given colour name's swatch."""
    return _ink_for(COLOR_HEX.get((name or "").lower(), "#ccc"))


@register.simple_tag(takes_context=True)
def query_with(context, **kwargs):
    """Current querystring with some keys replaced: {% query_with color='black' %}."""
    params = context["request"].GET.copy()
    for k, v in kwargs.items():
        if v in (None, ""):
            params.pop(k, None)
        else:
            params[k] = v
    encoded = params.urlencode()
    return f"?{encoded}" if encoded else "?"
