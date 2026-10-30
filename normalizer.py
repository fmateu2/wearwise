import json
import os

from dotenv import load_dotenv

load_dotenv()  # Load environment variables.

# load normalization file
with open(os.getenv("NORMALIZATION_CONFIG_PATH"), "r") as f:
    CONFIG = json.load(f)["normalization"]


def normalize_value(value, dictionary):
    "Normalizes an attribute with the corresponding dictionary in normalization"

    if not value:
        return None
    key = value.strip().lower()
    return dictionary.get(key, value)


def normalize_garment(garment):
    "Normalize attributes for a single garment."

    raw_type = garment.get("garment_type", "").lower().strip()

    category = CONFIG["categories"].get(raw_type, raw_type)

    # returns the normalized garment dictionary
    return {
        "garment_type": category,
        "specific_type": raw_type,
        "sex": garment.get("sex"),
        "color": normalize_value(garment.get("color"), CONFIG["colors"]),
        "pattern": normalize_value(garment.get("pattern"), CONFIG["patterns"]),
        "season": normalize_value(garment.get("season"), CONFIG["seasons"]),
        "material": normalize_value(garment.get("material"), CONFIG["materials"]),
        "style": normalize_value(garment.get("style"), CONFIG["styles"]),
        "formality": normalize_value(garment.get("formality"), CONFIG["formality"]),
        "occasion": normalize_value(garment.get("occasion"), CONFIG["occasions"]),
    }


def normalize_attributes(raw):
    "Normalize all extracted attributes for each garment."

    garments = raw.get(
        "garments", []
    )  # creates list of garments (if theres an error the list is empty -> avoid crashes)
    normalized = [normalize_garment(g) for g in garments]

    return {"garments": normalized}
