import pytest
from backend.services.input_validator import validate_dynamic_inputs

def test_dynamic_text_and_number_validation():
    field_defs = [
        {"name": "topic", "type": "text", "is_required": True, "validation_rules": {"min_length": 3}},
        {"name": "word_count", "type": "number", "is_required": False, "default_value": "500", "validation_rules": {"min": 50, "max": 5000}},
        {"name": "include_citations", "type": "boolean", "is_required": False, "default_value": "false"},
        {"name": "config", "type": "json", "is_required": False}
    ]

    # Valid payload
    payload = {
        "topic": "Quantum Computing",
        "word_count": "1000",
        "include_citations": "true",
        "config": '{"level": "advanced"}'
    }
    res = validate_dynamic_inputs(field_defs, payload)
    assert res.is_valid is True
    assert res.cleaned_data["topic"] == "Quantum Computing"
    assert res.cleaned_data["word_count"] == 1000
    assert res.cleaned_data["include_citations"] is True
    assert res.cleaned_data["config"] == {"level": "advanced"}

def test_missing_required_field():
    field_defs = [
        {"name": "topic", "type": "text", "is_required": True},
    ]
    res = validate_dynamic_inputs(field_defs, {})
    assert res.is_valid is False
    assert any("Missing required" in err for err in res.errors)

def test_text_length_and_number_range():
    field_defs = [
        {"name": "code", "type": "text", "is_required": True, "validation_rules": {"min_length": 5, "max_length": 10}},
        {"name": "score", "type": "number", "is_required": True, "validation_rules": {"min": 0, "max": 100}}
    ]

    # Too short text & score out of bounds
    res = validate_dynamic_inputs(field_defs, {"code": "abc", "score": 150})
    assert res.is_valid is False
    assert len(res.errors) == 2

def test_image_base64_input():
    field_defs = [
        {"name": "card_image", "type": "image", "is_required": True}
    ]
    res = validate_dynamic_inputs(field_defs, {"card_image": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="})
    assert res.is_valid is True
    assert len(res.images) == 1
    assert res.images[0].mime_type == "image/png"
    assert len(res.images[0].base64_data) > 0
