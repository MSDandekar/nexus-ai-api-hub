import json
from typing import Any, Optional
from pydantic import BaseModel

class SchemaValidationResult(BaseModel):
    is_valid: bool
    data: Optional[Any] = None
    errors: list[str] = []
    normalized: bool = False

def parse_schema_def(raw_schema: Any) -> dict:
    if not raw_schema:
        return {}
    if isinstance(raw_schema, dict):
        return raw_schema
    if isinstance(raw_schema, str):
        try:
            return json.loads(raw_schema)
        except Exception:
            return {}
    return {}

def coerce_type(val: Any, expected_type: str) -> tuple[Any, bool]:
    """Attempts safe type coercion. Returns (coerced_value, success)"""
    expected = expected_type.lower()
    if val is None:
        return None, True

    if expected in ("string", "str", "text"):
        if isinstance(val, (dict, list)):
            return json.dumps(val), True
        return str(val), True

    elif expected in ("number", "float", "int", "integer"):
        if isinstance(val, (int, float)):
            return val, True
        if isinstance(val, str):
            try:
                num = float(val) if "." in val else int(val)
                return num, True
            except ValueError:
                return val, False
        return val, False

    elif expected in ("boolean", "bool"):
        if isinstance(val, bool):
            return val, True
        if isinstance(val, str):
            lower = val.lower().strip()
            if lower in ("true", "1", "yes", "on"):
                return True, True
            if lower in ("false", "0", "no", "off"):
                return False, True
        if isinstance(val, (int, float)):
            return bool(val), True
        return val, False

    elif expected in ("array", "list"):
        if isinstance(val, list):
            return val, True
        if isinstance(val, (str, dict, int, float, bool)):
            return [val], True
        return val, False

    elif expected in ("object", "dict", "json"):
        if isinstance(val, dict):
            return val, True
        if isinstance(val, str):
            try:
                parsed = json.loads(val)
                if isinstance(parsed, dict):
                    return parsed, True
            except Exception:
                pass
        return val, False

    return val, True

def validate_and_normalize_schema(data: Any, schema_def: Any) -> SchemaValidationResult:
    schema = parse_schema_def(schema_def)
    if not schema:
        # No specific schema enforced, data passes through
        return SchemaValidationResult(is_valid=True, data=data, errors=[], normalized=False)

    if not isinstance(data, dict):
        return SchemaValidationResult(
            is_valid=False,
            data=data,
            errors=[f"Expected structured JSON object (dict), got {type(data).__name__}"],
            normalized=False
        )

    # If schema uses standard JSON Schema {"properties": {...}, "required": [...]}
    is_standard_json_schema = "properties" in schema and isinstance(schema["properties"], dict)
    properties = schema["properties"] if is_standard_json_schema else schema
    required_keys = schema.get("required", []) if is_standard_json_schema else list(properties.keys())

    normalized_data = dict(data)
    errors = []
    normalized_flag = False

    for key, spec in properties.items():
        expected_type = "string"
        if isinstance(spec, str):
            expected_type = spec
        elif isinstance(spec, dict):
            expected_type = spec.get("type", "string")

        if key not in normalized_data or normalized_data[key] is None:
            if key in required_keys:
                # Missing required field
                # Check if we can provide a default zero/empty value for repair
                if expected_type in ("array", "list"):
                    normalized_data[key] = []
                    normalized_flag = True
                elif expected_type in ("object", "dict"):
                    normalized_data[key] = {}
                    normalized_flag = True
                elif expected_type in ("string", "str"):
                    normalized_data[key] = ""
                    normalized_flag = True
                else:
                    errors.append(f"Required schema field '{key}' is missing from AI response.")
            continue

        raw_val = normalized_data[key]
        coerced_val, success = coerce_type(raw_val, expected_type)
        if success:
            if coerced_val != raw_val:
                normalized_flag = True
            normalized_data[key] = coerced_val
        else:
            errors.append(f"Field '{key}' could not be coerced to expected type '{expected_type}' (got {type(raw_val).__name__})")

    return SchemaValidationResult(
        is_valid=(len(errors) == 0),
        data=normalized_data,
        errors=errors,
        normalized=normalized_flag
    )
