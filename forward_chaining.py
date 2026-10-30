def garment_to_facts(garment):
    """
    Translates a garment dictionary into a set of discrete facts for the inference engine.
    Receives garment (dict) containing normalized attributes.
    returns tuple:
        garment_key identifier
        facts set
    """

    facts = set()
    garment_key = garment.get("filename")
    if garment_key:
        facts.add(f"garment:{garment_key}")

    attrs = garment.get("normalized_attributes", {})

    gtype = attrs.get("garment_type")
    if gtype:
        facts.add(f"garment_type:{gtype}")

    color = attrs.get("color")
    if color:
        # separates multiple colors (connected with and) and removes whitespaces
        # appending every color as a separate fact
        parts = [c.strip() for c in color.split("and")]
        for c in parts:
            if c:
                facts.add(f"color:{c}")

    # adding other attributes as facts
    for key in ["pattern", "season", "style", "formality", "occasion", "material"]:
        val = attrs.get(key)
        # safety check sometimes pattern or material can be None
        if val:
            facts.add(f"{key}:{val}")

    return garment_key, facts


def build_user_facts(user_input):
    """
    Converts user context into a set of logic facts.
    Receives user_input (dict): A dictionary containing user context
        example {"season": "summer", "temperature": 25}

    Outputs a set: A set of formatted string facts
        example {"season:summer", "temperature:25"}
    """
    facts = set()
    for k, v in user_input.items():
        # skip empty values
        if v is None or v == "":
            continue
        facts.add(f"{k}:{v}")
    return facts


def forward_chain(facts, wardrobe_rules):
    """
    Given the initial set of facts from the user derives new facts with the wardrobe rules.
    """
    rules = wardrobe_rules["rules"]
    changed = True
    while changed:
        changed = False

        # temperature rules
        temp_fact = next((f for f in facts if f.startswith("temperature:")), None)
        if temp_fact:
            temp_val = float(temp_fact.split(":", 1)[1])
            for tr in rules["temperature_rules"]["rules"]:
                if tr["min"] <= temp_val <= tr["max"]:
                    band_fact = f"temp_band:{tr['name']}"
                    if band_fact not in facts:
                        facts.add(band_fact)
                        changed = True
                    for req in tr.get("required", []):
                        rf = f"need:{req}"
                        if rf not in facts:
                            facts.add(rf)
                            changed = True
                    for forb in tr.get("forbidden", []):
                        ff = f"forbid:{forb}"
                        if ff not in facts:
                            facts.add(ff)
                            changed = True
                    break

        # formality rules
        formality_fact = next((f for f in facts if f.startswith("formality:")), None)
        if formality_fact:
            formality = formality_fact.split(":", 1)[1]
            allowed = rules["formality_rules"].get(formality, {}).get("allowed", [])
            for item in allowed:
                af = f"allowed_item:{item}"
                if af not in facts:
                    facts.add(af)
                    changed = True
            forbidden = rules["formality_rules"].get(formality, {}).get("forbidden", [])
            for item in forbidden:
                ff = f"forbid:{item}"
                if ff not in facts:
                    facts.add(ff)
                    changed = True

        # pattern rules
        pattern_fact = next((f for f in facts if f.startswith("pattern:")), None)
        if pattern_fact:
            p = pattern_fact.split(":", 1)[1]
            compatibles = rules["pattern_rules"].get(p, [])
            for cp in compatibles:
                pf = f"compatible_with_pattern:{cp}"
                if pf not in facts:
                    facts.add(pf)
                    changed = True

        # color rules
        color_facts = [f for f in facts if f.startswith("color:")]
        compat_map = rules["color_matching"]["compatible_colors"]
        for cf in color_facts:
            c = cf.split(":", 1)[1].strip()
            compatibles = compat_map.get(c, [])
            for cc in compatibles:
                ccf = f"compatible_with_color:{cc}"
                if ccf not in facts:
                    facts.add(ccf)
                    changed = True

        # occasion rules
        occasion_fact = next((f for f in facts if f.startswith("occasion:")), None)
        if occasion_fact:
            occasion = occasion_fact.split(":", 1)[1]

            occ_rules = rules.get("occasion_rules", {}).get(occasion, {})

            for item in occ_rules.get("allowed", []):
                af = f"allowed_item:{item}"
                if af not in facts:
                    facts.add(af)
                    changed = True

            # forbidding specific styles
            for style in occ_rules.get("forbidden_styles", []):
                sf = f"forbid_style:{style}"
                if sf not in facts:
                    facts.add(sf)
                    changed = True

            # forbidding specific items
            for item in occ_rules.get("forbidden_items", []):
                ff = f"forbid:{item}"
                if ff not in facts:
                    facts.add(ff)
                    changed = True

    return facts


def is_garment_safe(garment, user_facts, user_season):
    """
    Decides phisical suitability of a garment.
    Ignores fashion rules and focuses on comfort and survival.
    """
    attrs = garment.get("normalized_attributes", {})
    g_category = attrs.get("garment_type")
    g_specific = attrs.get("specific_type")
    g_season = attrs.get("season")
    g_style = attrs.get("style")

    # style restrictions from occasion rules
    if g_style and f"forbid_style:{g_style}" in user_facts:
        return False

    # temperature bounds
    if f"forbid:{g_category}" in user_facts:
        return False
    if g_specific and f"forbid:{g_specific}" in user_facts:
        return False

    # season compatibility
    if user_season == "summer" and g_season in ["winter", "autumn"]:
        return False
    if user_season == "winter" and g_season == "summer":
        return False

    return True


def is_garment_strict_match(garment, user_facts):
    """
    Returns true if the garment matches all strict rules (social context).
    """
    attrs = garment.get("normalized_attributes", {})
    g_specific = attrs.get("specific_type")

    # formality
    allowed_types = {f.split(":")[1] for f in user_facts if f.startswith("allowed_item:")}
    if allowed_types:
        # Check against allowed items
        if g_specific and g_specific not in allowed_types:
            return False

    return True


def calculate_score(garment, user_facts, user_formality):
    """
    If an item is safe and suitable, calculates score to get best match.

    +10 points: If the item matches the specific occasion (e.g., "Running Shoes" for "Gym").
    +5 points: If the item matches the exact formality level.
    +5 points: If it matches user preferences (e.g., user likes "Cotton").
    +3 points: If the color is compatible with the outfit palette.
    -5 points: Penalizes items that don't match the occasion (unless it's a coat, which is neutral).
    """

    garment_key, garment_facts = garment_to_facts(garment)
    combined = set(user_facts) | set(garment_facts)
    attrs = garment.get("normalized_attributes", {})
    score = 0

    # occasion
    g_occasion = attrs.get("occasion")
    user_occasion = next((f.split(":")[1] for f in user_facts if f.startswith("occasion:")), None)
    if user_occasion and g_occasion:
        if user_occasion == g_occasion:
            score += 10
        elif attrs.get("garment_type") != "outerwear":
            score -= 5

    # formality
    if user_formality and attrs.get("formality") == user_formality:
        score += 5

    # compatibility
    garment_colors = [f.split(":", 1)[1] for f in garment_facts if f.startswith("color:")]
    for gc in garment_colors:
        if f"compatible_with_color:{gc}" in combined:
            score += 3

    # user preference
    for key in ["material", "style", "color"]:
        uf = next((f for f in user_facts if f.startswith(f"{key}:")), None)
        if uf and uf in garment_facts:
            score += 5

    return score


# Helper to find best available candidate
def find_best(g_type_list, strict_candidates, fallback_candidates):
    for score, g in strict_candidates:
        if g.get("normalized_attributes", {}).get("garment_type") in g_type_list:
            return g
    for score, g in fallback_candidates:
        if g.get("normalized_attributes", {}).get("garment_type") in g_type_list:
            return g
    return None


def recommend_outfit_forward_chaining(user_input, garments, wardrobe_rules):
    """ "
    Calls forward_chain to fire rules based on input
    Rejects unsafe garments and scores the rest optimizing for best match.
    -> Picks the highest-scoring Top, Bottom, and Shoes.
    Checks the needed_items list.
    """

    # forward chain to expand facts
    user_facts = build_user_facts(user_input)
    user_facts = forward_chain(user_facts, wardrobe_rules)

    user_season = next((f.split(":")[1] for f in user_facts if f.startswith("season:")), None)
    user_formality = next((f.split(":")[1] for f in user_facts if f.startswith("formality:")), None)

    # required outfit items
    needed_items = {f.split(":")[1] for f in user_facts if f.startswith("need:")}

    strict_candidates = []
    fallback_candidates = []

    # filter and score garments
    for garment in garments:
        if not is_garment_safe(garment, user_facts, user_season):
            continue

        score = calculate_score(garment, user_facts, user_formality)

        if is_garment_strict_match(garment, user_facts):
            strict_candidates.append((score, garment))
        else:
            # fallback candidates to avoid empty response
            fallback_candidates.append((score - 20, garment))

    # sort by score
    strict_candidates.sort(key=lambda x: x[0], reverse=True)
    fallback_candidates.sort(key=lambda x: x[0], reverse=True)

    outfit = {"top": None, "bottom": None, "shoes": None, "extra": []}

    # Assemble Core Outfit
    outfit["top"] = find_best(["top"], strict_candidates, fallback_candidates)
    outfit["bottom"] = find_best(["bottom"], strict_candidates, fallback_candidates)
    outfit["shoes"] = find_best(["shoes"], strict_candidates, fallback_candidates)

    selected_ids = {g["_id"] for g in outfit.values() if g}

    for need in needed_items:
        # map common winter items to 'outerwear'
        if need in ["coat", "jacket", "puffer jacket", "parka", "trench coat", "blazer"]:
            target_type = "outerwear"
        elif need in ["boots", "sneakers", "sandals", "heels"]:
            target_type = "shoes"
        else:
            target_type = need

        # skip if we already filled the shoes slot with the right item
        if target_type == "shoes" and outfit["shoes"]:
            continue

        # try strict candidates first
        found = False
        for score, g in strict_candidates:
            if g["_id"] not in selected_ids:
                g_attrs = g.get("normalized_attributes", {})
                g_cat = g_attrs.get("garment_type")
                g_specific = g_attrs.get("specific_type")

                # match if category matches or specific name matches
                if g_cat == target_type or g_specific == need:
                    outfit["extra"].append(g)
                    selected_ids.add(g["_id"])
                    found = True
                    break

        # try fallback candidates
        if not found:
            for score, g in fallback_candidates:
                if g["_id"] not in selected_ids:
                    g_attrs = g.get("normalized_attributes", {})
                    g_cat = g_attrs.get("garment_type")

                    if g_cat == target_type:
                        outfit["extra"].append(g)
                        selected_ids.add(g["_id"])
                        break

    return outfit
