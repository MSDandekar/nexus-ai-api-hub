import pytest
from backend.services.schema_engine import validate_and_normalize_schema

def test_schema_valid_and_normalization():
    schema = {
        "name": "string",
        "age": "number",
        "is_active": "boolean",
        "tags": "array"
    }

    # Pass in string for age and single string for tags
    raw_data = {
        "name": "Alice Smith",
        "age": "28",
        "is_active": "true",
        "tags": "engineer"
    }

    res = validate_and_normalize_schema(raw_data, schema)
    assert res.is_valid is True
    assert res.data["name"] == "Alice Smith"
    assert res.data["age"] == 28
    assert res.data["is_active"] is True
    assert res.data["tags"] == ["engineer"]

def test_schema_missing_required():
    schema = {
        "name": "string",
        "score": "number"
    }
    raw_data = {
        "name": "Bob"
    }
    res = validate_and_normalize_schema(raw_data, schema)
    assert res.is_valid is False
    assert any("score" in err for err in res.errors)
