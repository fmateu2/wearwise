from dotenv import load_dotenv
from normalizer import normalize_attributes
from openai import OpenAI
import json
import base64

# Load environment variables (e.g., OPENAI_API_KEY) before creating the client
load_dotenv()
client = OpenAI()

BASE_PROMPT = """
You are a fashion attribute extraction expert. Detect ALL visible clothing items and footwear in the image.
Ignore non-wearable objects and small jewelry.

Return strict JSON:
{
  "garments": [
    {
      "garment_type": "...",
      "sex": "male|female|unisex",
      "color": "...",
      "pattern": "...",
      "material": "...",
      "season": "winter|summer|spring|autumn",
      "style": "street|chic|casual|vintage|minimalist|classic",
      "formality": "formal|business_casual|casual|sport",
      "occasion": "date|work|gym|party|beach|travel"
    }
  ]
}

Rules:
- Include one entry per visible item (clothing or shoes).
- Treat shoes/footwear as a valid 'garment_type'.
- Keep values concise; if unsure set value to null.
- Do not add outfit/grouping metadata.
"""


def extract_raw_attributes(image_bytes):
    """Call OpenAI Vision to extract structured attributes for all garments."""
    # Encode image bytes to base64 for the chat vision payload
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": BASE_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Extract attributes for every visible garment piece."},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"},
                    },
                ],
            },
        ],
        response_format={"type": "json_object"},
    )

    message = response.choices[0].message
    # Extract the JSON text from the content blocks
    if isinstance(message.content, str):
        text = message.content.strip()
    else:
        blocks = message.content or []
        parts = [block.text for block in blocks if getattr(block, "text", None)]
        text = "".join(parts).strip()

    if not text:
        raise ValueError("No text content returned from the model.")

    return json.loads(text)


def validate_and_enrich(raw):
    """
    Cleans and standardizes raw garment attributes using a second LLM pass.

    raw (dict): The initial dictionary of garment attributes extracted from the image.
    dict: A cleaned and validated dictionary of garment attributes, with standardized
          types and filtered invalid entries.
    ValueError: If the model returns an empty response.
    """
    # This is the prompt sent to validate and improve attributes (corrected attributes)
    validation_prompt = f"""
    You previously extracted these items:

    {json.dumps(raw, indent=2)}

    Validate and improve while keeping the same JSON shape:
    - Ensure 'garment_type' is a standard fashion term (e.g., 'jeans', 'dress', 'sneakers', 'boots', 'jacket').
    - Correct spelling errors.
    - If an attribute is unclear, leave it null.
    - Do not remove items unless they are clearly non-fashion objects (e.g., hangers, text overlays).
    - Preserve footwear and accessories.

    Respond in JSON only, same structure.
    """
    # standard method in the OpenAI python library
    response = client.chat.completions.create(
        model="gpt-4o-mini",  # selecting model (mini version for faster responses)
        messages=[
            {"role": "user", "content": validation_prompt}
        ],  # sending the previous prompt simulating user input
        response_format={"type": "json_object"},  # constraint to return JSON object
    )

    message = response.choices[0].message  # (ChatGPT can return multiple choices, take default)
    text = message.content.strip()

    # raises error if invalid output is produced
    if not text:
        raise ValueError("Error: Empty response.")

    # transform the string to a dictionary (allows to manipulate data as python objects)
    return json.loads(text)


def run_agent(image_bytes):
    """
    extracts, validates, and normalizes fashion attributes from a raw image.
        raw extraction: OpenAI Vision to detect initial attributes.
        validation: fines down attributes using a secondary LLM pass (standardization).
        normalization: Maps specific terms to the system's internal definitons.

    image_bytes (bytes): The raw byte content of the image file.

    dict: A dictionary containing the data at each stage of processing:
        "raw": The initial JSON output from the vision model.
        "corrected": The validated and tuned JSON data.
        "normalized": The final data mapped to internal categories.
    """

    raw = extract_raw_attributes(image_bytes)

    # second pass to validate
    corrected = validate_and_enrich(raw)

    normalized = normalize_attributes(corrected)

    return {"raw": raw, "corrected": corrected, "normalized": normalized}
