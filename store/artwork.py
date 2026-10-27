"""Product artwork: each piece rendered as a flat-lay — a filled silhouette with a fabric texture
chosen from its material, soft light and a cast shadow — until a real photograph is uploaded.

All SVG here is built from constants and validated colours; no user text reaches the markup.
"""

import re
import uuid

# silhouettes on a 200x260 canvas. fill: closed shapes; straps: thick strokes in the garment colour;
# detail: seams, buttons and pockets drawn quietly on top
SHAPES = {
    "dresses": {
        "fill": ["M86 30 Q100 42 114 30 L118 36 L111 94 L148 228 Q100 240 52 228 L89 94 L82 36 Z"],
        "straps": ["M86 31 L89 12", "M114 31 L111 12"],
        "detail": '<path d="M90 94 Q100 99 110 94"/><path d="M97 102 L86 224 M104 102 L115 224" opacity=".5"/>',
    },
    "t-shirts": {
        "fill": ["M72 42 L90 32 Q100 44 110 32 L128 42 L156 68 L140 86 L128 74 L128 200 L72 200 L72 74 L60 86 L44 68 Z"],
        "detail": '<path d="M90 32 Q100 50 110 32"/><path d="M72 192 L128 192 M48 72 L60 84 M152 72 L140 84" opacity=".55"/>',
    },
    "shirts": {
        "fill": ["M74 40 L92 30 L100 46 L108 30 L126 40 L150 146 L136 150 L124 84 L124 204 L76 204 L76 84 L64 150 L50 146 Z"],
        "detail": ('<path d="M92 30 L95 52 L100 46 L105 52 L108 30"/><path d="M101 46 L101 204"/>'
                   '<circle cx="104" cy="74" r="1.4"/><circle cx="104" cy="104" r="1.4"/><circle cx="104" cy="134" r="1.4"/>'
                   '<circle cx="104" cy="164" r="1.4"/><path d="M80 64 L94 64 L94 80 L80 80 Z" opacity=".6"/>'
                   '<path d="M52 140 L64 144 M148 140 L136 144" opacity=".6"/>'),
    },
    "knitwear": {
        "fill": ["M72 42 Q100 58 128 42 L152 60 L164 172 L146 175 L132 92 L132 200 L68 200 L68 92 L54 175 L36 172 L48 60 Z"],
        "detail": ('<path d="M84 46 Q100 64 116 46"/><path d="M80 50 Q100 70 120 50" opacity=".5"/>'
                   '<path d="M68 186 L132 186 M38 160 L54 163 M146 163 L162 160" opacity=".6"/>'),
    },
    "trousers": {
        "fill": ["M70 28 L130 28 L137 230 L108 230 L100 92 L92 230 L63 230 Z"],
        "detail": '<path d="M70 40 L130 40"/><path d="M84 46 L80 228 M116 46 L120 228" opacity=".45"/><path d="M100 40 L100 92" opacity=".6"/>',
    },
    "jeans": {
        "fill": ["M70 28 L130 28 L137 230 L108 230 L100 92 L92 230 L63 230 Z"],
        "detail": ('<path d="M70 40 L130 40"/><path d="M74 46 Q84 62 96 50 M126 46 Q116 62 104 50"/><path d="M100 40 L100 92"/>'
                   '<path d="M66 222 L92 222 M108 222 L136 222 M72 42 L72 60 M128 42 L128 60" stroke-dasharray="1.6 2.4" opacity=".8"/>'),
    },
    "skirts": {
        "fill": ["M76 48 L124 48 L152 204 Q100 216 48 204 Z"],
        "detail": '<path d="M76 60 L124 60"/><path d="M88 60 L74 206 M100 60 L100 210 M112 60 L126 206" opacity=".4"/>',
    },
    "shorts": {
        "fill": ["M68 70 L132 70 L140 162 L106 166 L100 112 L94 166 L60 162 Z"],
        "detail": '<path d="M68 82 L132 82"/><path d="M100 82 L100 112" opacity=".6"/><path d="M62 152 L94 156 M106 156 L138 152" opacity=".5"/>',
    },
    "blazers": {
        "fill": ["M66 36 L92 28 L100 112 L108 28 L134 36 L154 60 L162 192 L146 194 L136 102 L136 214 L64 214 L64 102 L54 194 L38 192 L46 60 Z"],
        "detail": ('<path d="M92 28 L82 72 L100 112 M108 28 L118 72 L100 112"/><path d="M100 112 L100 214" opacity=".5"/>'
                   '<circle cx="105" cy="136" r="2"/><circle cx="105" cy="160" r="2"/>'
                   '<path d="M72 168 L90 168 M110 168 L128 168 M114 88 L128 88" opacity=".6"/>'),
    },
    "coats": {
        "fill": ["M68 30 L92 24 L100 72 L108 24 L132 30 L154 56 L164 212 L148 214 L138 102 L144 248 L56 248 L62 102 L52 214 L36 212 L46 56 Z"],
        "detail": ('<path d="M92 24 L80 60 L100 72 M108 24 L120 60 L100 72"/><path d="M62 132 L138 132"/>'
                   '<path d="M100 72 L100 248" opacity=".5"/><circle cx="92" cy="96" r="2"/><circle cx="92" cy="170" r="2"/>'
                   '<circle cx="108" cy="96" r="2"/><circle cx="108" cy="170" r="2"/>'),
    },
    "shoes": {
        "fill": ["M34 176 Q38 146 70 142 L108 138 Q124 122 146 132 Q170 144 172 176 Z", "M32 176 L174 176 L174 186 L32 186 Z"],
        "detail": '<path d="M96 140 Q112 156 130 134"/><path d="M40 172 Q100 168 166 172" opacity=".5"/>',
    },
    "accessories": {
        "fill": ["M56 104 L144 104 L154 214 L46 214 Z"],
        "straps": ["M76 104 Q76 54 100 54 Q124 54 124 104"],
        "detail": '<path d="M56 104 L100 146 L144 104"/><circle cx="100" cy="146" r="3"/>',
    },
}

# material keywords -> texture family (first match wins)
TEXTURE_RULES = [
    (("denim", "selvedge"), "denim"),
    (("raffia", "straw", "toquilla", "canvas"), "weave"),
    (("silk", "satin", "charmeuse", "crêpe", "crepe", "viscose"), "satin"),
    (("linen",), "linen"),
    (("leather", "calfskin", "lambskin", "nappa", "suede", "calf", "goat"), "leather"),
    (("nylon", "down", "technical"), "quilted"),
    (("cashmere", "merino", "knit", "rib"), "knit"),
    (("wool", "gabardine", "flannel", "suiting", "twill", "tweed"), "twill"),
]

TEXTURES = {
    # pattern markup, drawn in black/white at low opacity over the garment colour
    "knit": ('<pattern id="{id}-tx" width="3.2" height="5" patternUnits="userSpaceOnUse">'
             '<path d="M0 0 L1.6 2.5 L0 5 M1.6 0 L3.2 2.5 L1.6 5" stroke="#000" stroke-opacity=".16" stroke-width=".55" fill="none"/></pattern>'),
    "twill": ('<pattern id="{id}-tx" width="2.6" height="2.6" patternUnits="userSpaceOnUse" patternTransform="rotate(-38)">'
              '<path d="M0 0 V2.6" stroke="#000" stroke-opacity=".13" stroke-width=".7"/></pattern>'),
    "denim": ('<pattern id="{id}-tx" width="2.2" height="2.2" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
              '<path d="M0 0 V2.2" stroke="#fff" stroke-opacity=".2" stroke-width=".7"/></pattern>'),
    "linen": ('<pattern id="{id}-tx" width="7" height="7" patternUnits="userSpaceOnUse">'
              '<path d="M0 1.5 H7 M0 4.8 H7" stroke="#000" stroke-opacity=".07" stroke-width=".8"/>'
              '<path d="M2 0 V7 M5.5 0 V7" stroke="#fff" stroke-opacity=".1" stroke-width=".6"/></pattern>'),
    "weave": ('<pattern id="{id}-tx" width="6" height="6" patternUnits="userSpaceOnUse">'
              '<path d="M0 0 H3 V3 H0 Z M3 3 H6 V6 H3 Z" fill="#000" fill-opacity=".1"/>'
              '<path d="M0 3 H6 M3 0 V6" stroke="#fff" stroke-opacity=".18" stroke-width=".5"/></pattern>'),
    "quilted": ('<pattern id="{id}-tx" width="200" height="18" patternUnits="userSpaceOnUse">'
                '<path d="M0 17 H200" stroke="#000" stroke-opacity=".22" stroke-width=".8"/>'
                '<rect y="2" width="200" height="8" fill="#fff" fill-opacity=".07"/></pattern>'),
    "satin": "",    # satin is all sheen, see SHEEN
    "leather": "",  # grain comes from the noise layer
    "cotton": "",
}

# light across the surface: satin and leather get a stronger, banded sheen
SHEEN = {
    "satin": [(0, .34), (.22, 0), (.48, .2), (.7, 0), (1, .1)],
    "leather": [(0, .18), (.35, 0), (.6, .08), (1, 0)],
    "quilted": [(0, .16), (.5, 0), (1, .06)],
}
DEFAULT_SHEEN = [(0, .14), (.5, 0), (1, 0)]
NOISE_OPACITY = {"leather": .22, "cotton": .1, "linen": .16, "knit": .12, "denim": .2, "weave": .14}

_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


def texture_for(product):
    text = f"{product.material} {product.category.slug}".lower()
    for words, family in TEXTURE_RULES:
        if any(w in text for w in words):
            return family
    return "cotton"


def _luminance(hex_color):
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _mix(hex_color, other, t):
    h, o = hex_color.lstrip("#"), other.lstrip("#")
    a = [int(h[i:i + 2], 16) for i in (0, 2, 4)]
    b = [int(o[i:i + 2], 16) for i in (0, 2, 4)]
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(a, b, strict=True))


def flat_lay_svg(product, swatch):
    """SVG markup for the product drawn in `swatch` (a validated #rrggbb colour)."""
    if not _HEX.match(swatch or ""):
        swatch = "#d6c7ad"
    shape = SHAPES.get(product.category.slug, SHAPES["t-shirts"])
    family = texture_for(product)
    uid = f"g{uuid.uuid4().hex[:8]}"
    light = _luminance(swatch) > 150
    seam = _mix(swatch, "#000000", .45) if light else _mix(swatch, "#ffffff", .34)
    edge = _mix(swatch, "#000000", .22)
    # pale cloth needs far less edge shadow or it turns grey and dirty
    lum = _luminance(swatch)
    edge_shadow = .12 if lum > 215 else .2 if lum > 170 else .34

    sheen_stops = "".join(f'<stop offset="{o}" stop-color="#fff" stop-opacity="{a}"/>' for o, a in SHEEN.get(family, DEFAULT_SHEEN))
    fills = "".join(f'<path d="{d}"/>' for d in shape["fill"])
    straps = "".join(
        f'<path d="{d}" fill="none" stroke="{swatch}" stroke-width="{4.5 if product.category.slug == "accessories" else 2.4}" stroke-linecap="round"/>'
        for d in shape.get("straps", [])
    )
    texture = TEXTURES[family].format(id=uid)
    texture_layer = f'<rect width="200" height="260" fill="url(#{uid}-tx)"/>' if texture else ""

    return (
        f'<svg viewBox="0 0 200 260" aria-hidden="true" class="flatlay flatlay--{family}">'
        "<defs>"
        f'<clipPath id="{uid}-clip">{fills}</clipPath>'
        f'<linearGradient id="{uid}-sheen" x1="0" y1="0" x2="1" y2="1">{sheen_stops}</linearGradient>'
        f'<linearGradient id="{uid}-shade" x1="0" y1="0" x2="0" y2="1"><stop offset=".55" stop-color="#000" stop-opacity="0"/>'
        '<stop offset="1" stop-color="#000" stop-opacity=".16"/></linearGradient>'
        f'<filter id="{uid}-shadow" x="-20%" y="-20%" width="140%" height="150%">'
        '<feDropShadow dx="0" dy="7" stdDeviation="7" flood-color="#2a2219" flood-opacity=".28"/></filter>'
        f'<filter id="{uid}-noise"><feTurbulence type="fractalNoise" baseFrequency="1.1" numOctaves="2" seed="{product.pk or 1}"/>'
        f'<feColorMatrix values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 {NOISE_OPACITY.get(family, .1)} 0"/></filter>'
        f'<radialGradient id="{uid}-light" cx=".42" cy=".3" r=".75"><stop offset="0" stop-color="#fff" stop-opacity=".26"/>'
        '<stop offset=".6" stop-color="#fff" stop-opacity="0"/></radialGradient>'
        f'<filter id="{uid}-soft" x="-10%" y="-10%" width="120%" height="120%"><feGaussianBlur stdDeviation="5"/></filter>'
        f"{texture}"
        "</defs>"
        # cast shadow, then the cloth (a same-colour round-joined stroke softens the cut corners)
        f'<g filter="url(#{uid}-shadow)">{straps}'
        f'<g fill="{swatch}" stroke="{swatch}" stroke-width="2.5" stroke-linejoin="round">{fills}</g></g>'
        f'<g clip-path="url(#{uid}-clip)">{texture_layer}'
        f'<rect width="200" height="260" filter="url(#{uid}-noise)"/>'
        f'<rect width="200" height="260" fill="url(#{uid}-light)"/>'
        f'<rect width="200" height="260" fill="url(#{uid}-sheen)"/>'
        f'<rect width="200" height="260" fill="url(#{uid}-shade)"/>'
        # volume: the cloth darkens as it turns away at the edges and along seams
        f'<g filter="url(#{uid}-soft)" fill="none" stroke="#1a140e" stroke-opacity="{edge_shadow}" stroke-width="16" stroke-linejoin="round">{fills}</g>'
        f'<g filter="url(#{uid}-soft)" fill="none" stroke="#1a140e" stroke-opacity="{edge_shadow * .6:.2f}" stroke-width="7">{shape["detail"]}</g></g>'
        f'<g fill="none" stroke="{edge}" stroke-width=".8" stroke-opacity=".6" stroke-linejoin="round">{fills}</g>'
        f'<g fill="none" stroke="{seam}" stroke-width="1.05" stroke-linecap="round" stroke-linejoin="round">'
        f'{shape["detail"]}</g>'
        "</svg>"
    )


def backdrop_for(swatch):
    """Paper sweep behind the piece: a shade darker for very pale garments so they don't disappear."""
    try:
        return "#ddd6ca" if _luminance(swatch) > 205 else "#e9e3d8"
    except (ValueError, IndexError):
        return "#e9e3d8"
