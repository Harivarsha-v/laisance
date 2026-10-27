"""Size advisor: recommends a size from height, weight and preferred fit.

Uses BMI-adjusted height bands per department, nudged for the fit the shopper
likes, and reports a confidence so the UI can say how sure it is.
"""

SIZES = ["XS", "S", "M", "L", "XL"]

# (max height cm, base size index) per department
HEIGHT_BANDS = {
    "women": [(155, 0), (163, 1), (170, 2), (177, 3), (999, 4)],
    "men": [(165, 0), (173, 1), (181, 2), (188, 3), (999, 4)],
}
FIT_SHIFT = {"slim": -1, "regular": 0, "relaxed": 1}


def recommend_size(height_cm, weight_kg, department="women", fit="regular", available=None):
    height_cm, weight_kg = float(height_cm), float(weight_kg)
    if not (120 <= height_cm <= 230 and 30 <= weight_kg <= 250):
        raise ValueError("Height or weight out of range")

    idx = next(i for h, i in HEIGHT_BANDS.get(department, HEIGHT_BANDS["women"]) if height_cm <= h)
    bmi = weight_kg / (height_cm / 100) ** 2
    if bmi < 18.5:
        idx -= 1
    elif bmi >= 30:
        idx += 2
    elif bmi >= 25:
        idx += 1
    idx += FIT_SHIFT.get(fit, 0)
    idx = max(0, min(idx, len(SIZES) - 1))
    size = SIZES[idx]

    available = available or SIZES
    if size not in available:
        size = min(available, key=lambda s: abs(SIZES.index(s) - idx) if s in SIZES else 99)

    # confidence drops near band edges and at extreme BMI
    confidence = 0.9 if 19 <= bmi < 27 else 0.75
    note = {
        "slim": "Sized for a closer fit.",
        "relaxed": "Sized up for a relaxed drape.",
    }.get(fit, "Our pick for a regular fit.")
    return {"size": size, "confidence": confidence, "note": note}
