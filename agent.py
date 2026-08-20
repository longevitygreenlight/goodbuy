"""GOODBUY — Strands agent. Tools decide the flags; the model only phrases them."""

import json
from pathlib import Path

from strands import Agent, tool
from strands.models import BedrockModel

from evaluate_cart import evaluate_cart, totals

MODEL_ID = "us.amazon.nova-2-lite-v1:0"
REGION = "us-east-1"

EXTRACT_PROMPT = """You are reading a screenshot of a grocery shopping cart.

Return ONLY valid JSON, no markdown fences, no commentary, in this shape:
{"lines": [{"raw_name": str, "size": str|null, "qty": int, "line_total": float|null, "promo_text": str|null, "category": str, "perishable": bool}],
 "advertised_saving": float|null}

Rules:
- Include a line ONLY if it is an item in the cart with a quantity.
- SKIP rows marked out of stock or unavailable, and skip anything with no quantity control.
- qty is the number shown in the quantity stepper.
- line_total is the rand amount printed on that row, exactly as shown. Never multiply it by qty.
- advertised_saving is the cart's stated saving, if one is shown.
- category is a short lowercase food category, e.g. "produce", "tinned goods", "dips", "dairy", "snacks".
- perishable is true if the item goes off within about a week, false for tinned, frozen or dry goods.
- Do not invent values. Use null when something is not visible."""


def _json_from(text):
    text = str(text)
    if "```" in text:
        text = text.split("```json")[-1].split("```")[0]
    return json.loads(text.strip())


@tool
def read_cart(image_path: str) -> dict:
    """Read a grocery cart screenshot and return its line items as structured data."""
    reader = Agent(
        model=BedrockModel(model_id=MODEL_ID, region_name=REGION),
        callback_handler=None,
    )
    result = reader([
        {"image": {"format": "jpeg", "source": {"bytes": Path(image_path).read_bytes()}}},
        {"text": EXTRACT_PROMPT},
    ])
    return _json_from(result)


@tool
def check_cart(cart: dict, household: int = 2, exclusions: list = None) -> dict:
    """Apply GOODBUY's deterministic rules to an extracted cart and return flags and totals."""
    flags = evaluate_cart(cart["lines"], household=household, exclusions=exclusions or [])
    return {"flags": flags, "totals": totals(flags, cart.get("advertised_saving"))}


SYSTEM = """You are GOODBUY, checking a grocery cart at checkout.

Call read_cart on the image, then check_cart on the result.

Then write the verdict. Rules for the verdict:
- Report ONLY the flags the tools returned. Never add a flag of your own, never drop one.
- One short line per flag, each carrying its reason inline.
- Say the rand amounts as the tools gave them. Do not recalculate.
- If flagged_total exceeds the advertised saving, say so in one closing line. Otherwise say nothing about it.
- No greeting, no summary, no advice beyond the flags. This is read at checkout."""

if __name__ == "__main__":
    agent = Agent(
        model=BedrockModel(model_id=MODEL_ID, region_name=REGION),
        system_prompt=SYSTEM,
        tools=[read_cart, check_cart],
    )
    agent("Check cart_test.jpg. Household is 2. Exclusions: tinned.")