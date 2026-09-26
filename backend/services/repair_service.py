import re
import json
from typing import Optional, Any
from backend.services.providers.base import AIProvider, ProviderResult
from backend.services.schema_engine import validate_and_normalize_schema, SchemaValidationResult

def extract_json_block(text: str) -> Optional[str]:
    """Extracts JSON block from text even if surrounded by commentary or markdown."""
    cleaned = text.strip()
    # Strip markdown block
    if "```json" in cleaned:
        match = re.search(r"```json\s*(.*?)\s*```", cleaned, re.DOTALL)
        if match:
            return match.group(1).strip()
    elif "```" in cleaned:
        match = re.search(r"```\s*(.*?)\s*```", cleaned, re.DOTALL)
        if match:
            return match.group(1).strip()

    # Search for outer braces
    first_brace = cleaned.find("{")
    last_brace = cleaned.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        return cleaned[first_brace:last_brace + 1]

    first_bracket = cleaned.find("[")
    last_bracket = cleaned.rfind("]")
    if first_bracket != -1 and last_bracket != -1 and last_bracket > first_bracket:
        return cleaned[first_bracket:last_bracket + 1]

    return None

def heuristic_json_fix(json_str: str) -> Optional[Any]:
    """Applies common JSON syntax fixes for trailing commas and unquoted keys."""
    try:
        return json.loads(json_str)
    except Exception:
        pass

    # Fix trailing commas: ,} -> } and ,] -> ]
    fixed = re.sub(r",\s*([\]}])", r"\1", json_str)
    try:
        return json.loads(fixed)
    except Exception:
        pass

    # Fix single quotes to double quotes for simple JSON
    fixed_quotes = re.sub(r"'([^']*)':", r'"\1":', fixed)
    try:
        return json.loads(fixed_quotes)
    except Exception:
        pass

    return None

class RepairResult:
    def __init__(self, success: bool, data: Any, method: str, error: Optional[str] = None):
        self.success = success
        self.data = data
        self.method = method  # "heuristic", "ai_repair", "none"
        self.error = error

async def attempt_response_repair(
    raw_text: str,
    schema_def: Optional[dict],
    provider: Optional[AIProvider] = None,
    model_id: Optional[str] = None
) -> RepairResult:
    """Attempts multi-stage repair on malformed response."""
    # Stage 1: Extraction & Heuristic repair
    extracted = extract_json_block(raw_text) or raw_text
    parsed = heuristic_json_fix(extracted)

    if parsed is not None:
        val_res = validate_and_normalize_schema(parsed, schema_def)
        if val_res.is_valid:
            return RepairResult(success=True, data=val_res.data, method="heuristic")

    # Stage 2: AI Repair prompt (one targeted attempt)
    if provider and model_id and provider.is_configured():
        try:
            repair_prompt = (
                f"The following output was expected to be valid JSON matching this schema:\n"
                f"{json.dumps(schema_def or {}, indent=2)}\n\n"
                f"However, the previous response was malformed or incomplete:\n"
                f"{raw_text[:2000]}\n\n"
                f"Please fix the syntax and format errors and return ONLY the valid raw JSON object. Do not include any explanations."
            )
            retry_res = await provider.generate(
                model_id=model_id,
                prompt=repair_prompt,
                json_schema=schema_def,
                temperature=0.0
            )
            extracted_retry = extract_json_block(retry_res.raw_text) or retry_res.raw_text
            parsed_retry = heuristic_json_fix(extracted_retry)
            if parsed_retry is not None:
                val_retry = validate_and_normalize_schema(parsed_retry, schema_def)
                if val_retry.is_valid:
                    return RepairResult(success=True, data=val_retry.data, method="ai_repair")
        except Exception as e:
            return RepairResult(success=False, data=None, method="failed", error=f"AI repair failed: {str(e)}")

    return RepairResult(success=False, data=None, method="failed", error="Unable to repair malformed JSON response.")
