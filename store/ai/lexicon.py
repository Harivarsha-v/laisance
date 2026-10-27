"""Fashion vocabulary the local AI uses to understand shoppers.

Everything here is plain data so it is easy to extend: add a synonym, an
occasion or a colour and the search, stylist and copywriter all pick it up.
"""

# canonical colour -> words shoppers might type
COLORS = {
    "black": ["black", "noir", "jet", "onyx"],
    "white": ["white", "optic", "snow"],
    "ecru": ["ecru", "cream", "ivory", "offwhite", "oat", "oatmeal"],
    "beige": ["beige", "sand", "stone", "taupe", "nude"],
    "camel": ["camel", "tan", "caramel", "cognac"],
    "brown": ["brown", "chocolate", "mocha", "coffee"],
    "grey": ["grey", "gray", "charcoal", "slate", "silver", "marl"],
    "navy": ["navy", "midnight", "ink"],
    "blue": ["blue", "denim", "cobalt", "sky", "indigo", "chambray"],
    "green": ["green", "olive", "khaki", "sage", "emerald", "forest"],
    "red": ["red", "burgundy", "wine", "cherry", "crimson", "maroon"],
    "pink": ["pink", "rose", "blush", "fuchsia"],
    "yellow": ["yellow", "butter", "mustard", "lemon", "gold"],
    "champagne": ["champagne", "satin-gold"],
}
COLOR_ALIASES = {alias: canon for canon, aliases in COLORS.items() for alias in aliases}

NEUTRALS = {"black", "white", "ecru", "beige", "camel", "brown", "grey", "navy", "champagne"}

# pairs of non-neutral colours that work well together (order doesn't matter)
GOOD_PAIRS = {
    frozenset(p)
    for p in [
        ("blue", "beige"), ("blue", "ecru"), ("blue", "white"), ("blue", "camel"),
        ("green", "ecru"), ("green", "beige"), ("green", "camel"), ("green", "brown"),
        ("red", "navy"), ("red", "black"), ("red", "ecru"),
        ("pink", "grey"), ("pink", "white"), ("pink", "navy"),
        ("yellow", "navy"), ("yellow", "white"), ("yellow", "grey"),
        ("blue", "pink"), ("green", "pink"),
    ]
}

DEPARTMENT_WORDS = {
    "women": ["women", "woman", "womens", "ladies", "lady", "her", "she", "girl", "girls", "female", "girlfriend", "wife", "mom"],
    "men": ["men", "man", "mens", "him", "he", "guy", "guys", "boy", "male", "boyfriend", "husband", "dad"],
}
DEPARTMENT_ALIASES = {w: d for d, words in DEPARTMENT_WORDS.items() for w in words}

# category slug -> words that mean it
CATEGORY_WORDS = {
    "t-shirts": ["tshirt", "tee", "tees", "top", "tops", "tank", "vest", "polo", "camisole"],
    "shirts": ["shirt", "shirts", "blouse", "blouses", "overshirt", "button"],
    "knitwear": ["knit", "knitwear", "sweater", "jumper", "cardigan", "pullover", "turtleneck", "hoodie", "sweatshirt"],
    "dresses": ["dress", "dresses", "gown", "frock", "jumpsuit"],
    "trousers": ["trouser", "trousers", "pant", "pants", "chino", "chinos", "slacks", "joggers"],
    "jeans": ["jean", "jeans", "denims"],
    "skirts": ["skirt", "skirts"],
    "shorts": ["shorts", "bermuda"],
    "blazers": ["blazer", "blazers", "suit", "suits", "tailoring", "waistcoat"],
    "coats": ["coat", "coats", "jacket", "jackets", "puffer", "parka", "trench", "bomber", "outerwear", "anorak"],
    "shoes": ["shoe", "shoes", "sneaker", "sneakers", "trainers", "boot", "boots", "heel", "heels", "loafer", "loafers", "sandal", "sandals", "mules", "footwear"],
    "accessories": ["bag", "bags", "belt", "belts", "scarf", "hat", "cap", "accessory", "accessories", "tote", "sunglasses", "jewellery", "jewelry"],
}
CATEGORY_ALIASES = {w: slug for slug, words in CATEGORY_WORDS.items() for w in words}

# words that imply related words; used to expand queries ("warm" finds wool coats)
SYNONYMS = {
    "warm": ["wool", "knit", "puffer", "coat", "cashmere", "winter", "padded"],
    "cosy": ["knit", "wool", "cashmere", "soft", "winter"],
    "cozy": ["knit", "wool", "cashmere", "soft", "winter"],
    "cold": ["wool", "coat", "puffer", "winter", "knit"],
    "light": ["linen", "cotton", "summer", "lightweight"],
    "breathable": ["linen", "cotton", "summer"],
    "hot": ["linen", "summer", "shorts", "sandals", "lightweight"],
    "smart": ["tailored", "blazer", "work", "formal", "wool"],
    "elegant": ["satin", "silk", "evening", "tailored", "formal"],
    "fancy": ["satin", "silk", "evening", "formal"],
    "comfy": ["soft", "relaxed", "jersey", "knit", "casual"],
    "comfortable": ["soft", "relaxed", "jersey", "casual"],
    "relaxed": ["oversized", "relaxed", "casual"],
    "baggy": ["oversized", "relaxed", "wide"],
    "fitted": ["slim", "tailored"],
    "minimal": ["clean", "basic", "essential"],
    "basic": ["essential", "cotton", "basic"],
    "rain": ["trench", "waterproof", "coat"],
    "sporty": ["sport", "active", "technical"],
    "edgy": ["leather", "street", "black"],
    "boho": ["linen", "summer", "flowing"],
    "classic": ["tailored", "essential", "wool", "trench"],
    "party": ["evening", "satin", "sequin"],
}

# occasion -> how to dress for it. "looks" are slot lists per department.
OCCASIONS = {
    "wedding": {
        "label": "a wedding",
        "triggers": ["wedding", "ceremony", "reception", "gala", "formal", "black-tie", "engagement"],
        "styles": ["formal", "evening"],
        "terms": ["tailored", "satin", "silk", "elegant", "formal"],
        "looks": {
            "women": [["one_piece", "shoes", "accessory"], ["top", "bottom", "shoes", "accessory"]],
            "men": [["outerwear", "top", "bottom", "shoes"]],
        },
        "prefer": {"outerwear": ["blazers"], "top": ["shirts"], "bottom": ["trousers", "skirts"]},
    },
    "work": {
        "label": "the office",
        "triggers": ["office", "work", "interview", "meeting", "business", "corporate", "professional", "job", "presentation"],
        "styles": ["work", "formal"],
        "terms": ["tailored", "smart", "wool", "crisp"],
        "looks": {
            "women": [["outerwear", "top", "bottom", "shoes"], ["one_piece", "outerwear", "shoes"]],
            "men": [["outerwear", "top", "bottom", "shoes"]],
        },
        "prefer": {"outerwear": ["blazers"], "top": ["shirts", "knitwear"], "bottom": ["trousers", "skirts"]},
    },
    "date": {
        "label": "dinner",
        "triggers": ["date", "dinner", "drinks", "romantic", "evening", "restaurant", "anniversary", "valentine"],
        "styles": ["evening", "casual"],
        "terms": ["satin", "silk", "leather", "evening", "fitted"],
        "looks": {
            "women": [["one_piece", "shoes", "accessory"], ["top", "bottom", "outerwear", "shoes"]],
            "men": [["top", "bottom", "outerwear", "shoes"]],
        },
        "prefer": {"bottom": ["trousers", "jeans", "skirts"]},
    },
    "party": {
        "label": "a party",
        "triggers": ["party", "club", "clubbing", "birthday", "celebration", "nye", "cocktail", "night"],
        "styles": ["evening", "street"],
        "terms": ["satin", "sequin", "leather", "evening", "bold"],
        "looks": {
            "women": [["one_piece", "shoes", "accessory"], ["top", "bottom", "shoes", "accessory"]],
            "men": [["top", "bottom", "outerwear", "shoes"]],
        },
        "prefer": {},
    },
    "beach": {
        "label": "the coast",
        "triggers": ["beach", "vacation", "holiday", "resort", "pool", "tropical", "island", "cruise", "seaside", "riviera", "capri", "mykonos", "summer house", "yacht"],
        "styles": ["casual"],
        "terms": ["linen", "cotton", "summer", "lightweight", "sandals"],
        "season": "summer",
        "looks": {
            "women": [["one_piece", "shoes", "accessory"], ["top", "bottom", "shoes", "accessory"]],
            "men": [["top", "bottom", "shoes", "accessory"]],
        },
        "prefer": {"bottom": ["shorts", "skirts", "trousers"], "top": ["shirts", "t-shirts"]},
    },
    "winter": {
        "label": "cold weather",
        "triggers": ["winter", "snow", "freezing", "cold", "christmas", "ski", "chilly"],
        "styles": ["casual", "work"],
        "terms": ["wool", "knit", "puffer", "cashmere", "warm"],
        "season": "winter",
        "looks": {
            "women": [["outerwear", "top", "bottom", "shoes"]],
            "men": [["outerwear", "top", "bottom", "shoes"]],
        },
        "prefer": {"outerwear": ["coats"], "top": ["knitwear"], "shoes": ["shoes"]},
    },
    "weekend": {
        "label": "the weekend",
        "triggers": ["weekend", "casual", "brunch", "everyday", "errands", "coffee", "chill", "relaxed", "school", "college", "uni", "class", "travel", "airport"],
        "styles": ["casual", "street"],
        "terms": ["cotton", "denim", "relaxed", "soft", "jersey"],
        "looks": {
            "women": [["top", "bottom", "outerwear", "shoes"], ["one_piece", "shoes", "accessory"]],
            "men": [["top", "bottom", "outerwear", "shoes"]],
        },
        "prefer": {"bottom": ["jeans", "trousers"], "top": ["t-shirts", "knitwear"]},
    },
    "street": {
        "label": "the city",
        "triggers": ["street", "streetwear", "concert", "festival", "gig", "city", "urban", "skate"],
        "styles": ["street", "casual"],
        "terms": ["oversized", "denim", "leather", "graphic", "relaxed"],
        "looks": {
            "women": [["top", "bottom", "outerwear", "shoes"]],
            "men": [["top", "bottom", "outerwear", "shoes"]],
        },
        "prefer": {"bottom": ["jeans", "trousers"]},
    },
}
OCCASION_TRIGGERS = {t: key for key, occ in OCCASIONS.items() for t in occ["triggers"]}

SEASON_WORDS = {
    "summer": ["summer", "hot", "sunny", "heat", "warm-weather"],
    "winter": ["winter", "cold", "snow", "freezing"],
    "transitional": ["spring", "autumn", "fall", "transitional"],
}
SEASON_ALIASES = {w: s for s, words in SEASON_WORDS.items() for w in words}

STOPWORDS = set(
    """a an and the of for to in on at with without by from or i me my we you your it its is are was be
    something some any anything need want looking look find show give get got have has please can could would
    like love really very just also what which that this these those so about into up out over than then
    there here im i'm id outfit outfits wear wearing go going dress-up help ideas idea new
    under below over above less more than max min budget dollars dollar bucks usd price cost around
    make try it show another different else other again one ones pls thx hi hello hey yo hiya
    thanks thank cheers great awesome perfect cool ok okay yes yeah sure""".split()
)

# when a message mentions several occasions, the more specific one wins
# ("beach wedding" is a wedding that happens to be on a beach)
OCCASION_PRIORITY = ["wedding", "work", "date", "party", "beach", "winter", "street", "weekend"]
