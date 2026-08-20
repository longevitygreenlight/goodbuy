"""Deterministic cart rules. No model decides a flag — it only phrases one."""

HARD = "dont_buy"
SOFT = "maybe_buy"


def evaluate_cart(lines, household=2, exclusions=None):
    exclusions = [e.lower() for e in (exclusions or [])]
    flags = []

    for line in lines:
        name = line["raw_name"]
        low = name.lower()

        # 1. Allergy or exclusion — hard refusal, never a suggestion.
        for ex in exclusions:
            if ex in low or ex in (line.get("category") or "").lower():
                flags.append({
                    "rule": "exclusion",
                    "class": HARD,
                    "raw_name": name,
                    "line_total": line.get("line_total"),
                    "evidence": f"{name} matches your exclusion '{ex}'",
                })

        # 2. Unit 2 of a perishable multi-buy for a small household.
        if line.get("perishable") and line.get("qty", 1) > 1:
            if line["qty"] > household:
                flags.append({
                    "rule": "spoilage",
                    "class": SOFT,
                    "raw_name": name,
                    "line_total": line.get("line_total"),
                    "evidence": f"{line['qty']} of {name} is fresh stock for {household} — unit {household + 1} onward spoils first",
                })

    # 3. Same product more than once in the cart.
    seen = {}
    for line in lines:
        key = line["raw_name"].lower()
        seen.setdefault(key, []).append(line)
    for key, group in seen.items():
        if len(group) > 1:
            flags.append({
                "rule": "duplicate",
                "class": HARD,
                "raw_name": group[0]["raw_name"],
                "line_total": sum(g.get("line_total") or 0 for g in group[1:]),
                "evidence": f"{group[0]['raw_name']} is in the cart {len(group)} times",
            })

    # 4. Category pile — several different products stacking up in one category.
    cats = {}
    for line in lines:
        cat = line.get("category")
        if cat:
            cats.setdefault(cat, []).append(line)
    for cat, group in cats.items():
        units = sum(g.get("qty", 1) for g in group)
        if len(group) > 1 and units > household + 1:
            flags.append({
                "rule": "category_pile",
                "class": SOFT,
                "raw_name": cat,
                "line_total": sum(g.get("line_total") or 0 for g in group),
                "evidence": f"{units} units of {cat} across {len(group)} products",
            })

    order = {HARD: 0, SOFT: 1}
    flags.sort(key=lambda f: order[f["class"]])
    return flags[:3]


def totals(flags, advertised_saving):
    hard = sum(f["line_total"] or 0 for f in flags if f["class"] == HARD)
    soft = sum(f["line_total"] or 0 for f in flags if f["class"] == SOFT)
    return {
        "dont_buy_total": round(hard, 2),
        "maybe_buy_total": round(soft, 2),
        "flagged_total": round(hard + soft, 2),
        "advertised_saving": advertised_saving,
        "exceeds_saving": (hard + soft) > (advertised_saving or 0),
    }