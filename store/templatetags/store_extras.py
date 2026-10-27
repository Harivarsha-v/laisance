"""Template helpers, including the illustrated garment artwork used until real photos are uploaded."""

from django import template
from django.utils.html import format_html
from django.utils.safestring import mark_safe

register = template.Library()

# fine line drawings per category, on a 200x260 canvas
GARMENTS = {
    "dresses": """
        <path d="M86 30 Q100 42 114 30 L118 36 L111 94 L148 228 Q100 240 52 228 L89 94 L82 36 Z"/>
        <path d="M86 30 L89 12 M114 30 L111 12"/><path d="M90 94 Q100 99 110 94"/>
        <path d="M96 100 L84 226 M104 100 L116 226" opacity=".45"/>""",
    "t-shirts": """
        <path d="M72 42 L90 32 Q100 44 110 32 L128 42 L156 68 L140 86 L128 74 L128 200 L72 200 L72 74 L60 86 L44 68 Z"/>
        <path d="M90 32 Q100 50 110 32" opacity=".5"/><path d="M72 192 L128 192" opacity=".45"/>""",
    "shirts": """
        <path d="M74 40 L92 30 L100 46 L108 30 L126 40 L150 146 L136 150 L124 84 L124 204 L76 204 L76 84 L64 150 L50 146 Z"/>
        <path d="M92 30 L95 52 L100 46 L105 52 L108 30"/><path d="M100 46 L100 204" opacity=".55"/>
        <circle cx="103" cy="74" r="1.6"/><circle cx="103" cy="104" r="1.6"/><circle cx="103" cy="134" r="1.6"/><circle cx="103" cy="164" r="1.6"/>
        <path d="M80 64 L94 64 L94 80 L80 80" opacity=".5"/>""",
    "knitwear": """
        <path d="M72 42 Q100 58 128 42 L152 60 L164 172 L146 175 L132 92 L132 200 L68 200 L68 92 L54 175 L36 172 L48 60 Z"/>
        <path d="M84 46 Q100 64 116 46"/><path d="M68 188 L132 188 M38 162 L54 164 M146 164 L162 162" opacity=".55"/>
        <path d="M80 96 L80 186 M90 96 L90 186 M100 96 L100 186 M110 96 L110 186 M120 96 L120 186" opacity=".18"/>""",
    "trousers": """
        <path d="M70 28 L130 28 L137 230 L108 230 L100 92 L92 230 L63 230 Z"/>
        <path d="M70 40 L130 40"/><path d="M84 46 L80 228 M116 46 L120 228" opacity=".35"/>
        <path d="M100 40 L100 92" opacity=".55"/>""",
    "jeans": """
        <path d="M70 28 L130 28 L137 230 L108 230 L100 92 L92 230 L63 230 Z"/>
        <path d="M70 40 L130 40"/><path d="M74 46 Q84 62 96 50 M126 46 Q116 62 104 50"/>
        <path d="M100 40 L100 92"/><path d="M66 220 L92 220 M108 220 L136 220" stroke-dasharray="2 3" opacity=".6"/>""",
    "skirts": """
        <path d="M76 48 L124 48 L152 204 Q100 216 48 204 Z"/>
        <path d="M76 60 L124 60"/><path d="M88 60 L74 206 M100 60 L100 210 M112 60 L126 206" opacity=".35"/>""",
    "shorts": """
        <path d="M68 70 L132 70 L140 162 L106 166 L100 112 L94 166 L60 162 Z"/>
        <path d="M68 82 L132 82"/><path d="M100 82 L100 112" opacity=".55"/>
        <path d="M62 152 L94 156 M106 156 L138 152" opacity=".4"/>""",
    "blazers": """
        <path d="M66 36 L92 28 L100 112 L108 28 L134 36 L154 60 L162 192 L146 194 L136 102 L136 214 L64 214 L64 102 L54 194 L38 192 L46 60 Z"/>
        <path d="M92 28 L82 72 L100 112 M108 28 L118 72 L100 112"/>
        <circle cx="104" cy="136" r="2"/><circle cx="104" cy="160" r="2"/>
        <path d="M72 168 L90 168 M110 168 L128 168 M114 88 L128 88" opacity=".5"/>""",
    "coats": """
        <path d="M68 30 L92 24 L100 72 L108 24 L132 30 L154 56 L164 212 L148 214 L138 102 L144 248 L56 248 L62 102 L52 214 L36 212 L46 56 Z"/>
        <path d="M92 24 L80 60 L100 72 M108 24 L120 60 L100 72"/><path d="M62 132 L138 132"/>
        <path d="M100 72 L100 248" opacity=".45"/><circle cx="92" cy="96" r="2"/><circle cx="92" cy="170" r="2"/>
        <circle cx="108" cy="96" r="2"/><circle cx="108" cy="170" r="2"/>""",
    "shoes": """
        <path d="M34 176 Q38 146 70 142 L108 138 Q124 122 146 132 Q170 144 172 176 Z"/>
        <path d="M32 176 L174 176 L174 186 L32 186 Z"/><path d="M96 140 Q112 156 130 134"/>
        <path d="M150 186 L150 176" opacity=".5"/>""",
    "accessories": """
        <path d="M56 104 L144 104 L154 214 L46 214 Z"/>
        <path d="M76 104 Q76 54 100 54 Q124 54 124 104"/><path d="M56 104 L100 146 L144 104"/>
        <circle cx="100" cy="146" r="3"/>""",
}


def _ink_for(hex_color):
    """Dark line work on light swatches, light line work on dark ones."""
    try:
        h = hex_color.lstrip("#")
        r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    except (ValueError, AttributeError):
        return "#1d1b18"
    luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return "#1d1b18" if luminance > 140 else "#f4efe6"


@register.simple_tag
def garment(product, css_class="", label=True, color=None):
    """Product artwork: the uploaded photo if there is one, otherwise the illustration (optionally recoloured)."""
    if product.image:
        return format_html(
            '<figure class="art {}"><img src="{}" alt="{}" loading="lazy"></figure>',
            css_class, product.image.url, product.name,
        )
    swatch = COLOR_HEX.get((color or "").lower(), product.swatch)
    ink = _ink_for(swatch)
    drawing = GARMENTS.get(product.category.slug, GARMENTS["t-shirts"])
    caption = (
        format_html('<figcaption><span>No. {}</span><span>{}</span></figcaption>', f"{product.pk:03d}", product.get_style_display())
        if label else ""
    )
    return format_html(
        '<figure class="art art--drawn {cls}" style="--swatch:{sw};--ink:{ink}" role="img" aria-label="{name}">'
        '<svg viewBox="0 0 200 260" fill="none" stroke="{ink}" stroke-width="1.15" stroke-linecap="round" '
        'stroke-linejoin="round" aria-hidden="true">{drawing}</svg>{caption}</figure>',
        cls=css_class, sw=swatch, ink=ink, name=product.name, drawing=mark_safe(drawing), caption=caption,
    )


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
