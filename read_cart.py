import json
from pathlib import Path
from strands import Agent
from strands.models import BedrockModel

PROMPT = """You are reading a screenshot of a grocery shopping cart.

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

model = BedrockModel(model_id="us.amazon.nova-2-lite-v1:0", region_name="us-east-1")
agent = Agent(model=model, callback_handler=None)

image_bytes = Path("cart_test.jpg").read_bytes()

result = agent([
    {"image": {"format": "jpeg", "source": {"bytes": image_bytes}}},
    {"text": PROMPT},
])

print(json.dumps(json.loads(str(result).split("```json")[-1].split("```")[0].strip()), indent=2))