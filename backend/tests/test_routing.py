import pytest
from backend.services.routing_engine import resolve_model_routing
from backend.services.repair_service import extract_json_block, heuristic_json_fix

def test_routing_vision_modality_filter():
    # If image attached, router MUST choose a model supporting vision
    decision = resolve_model_routing(
        strategy="cheapest",
        default_provider="openai",
        default_model="gpt-4o",
        has_images=True
    )
    assert decision.task_type == "vision"
    assert decision.selected_model in ["gemini-1.5-flash", "gemini-2.5-flash", "gpt-4o-mini", "llama-3.2-11b-vision-preview"]

def test_routing_strategies():
    # Fastest strategy
    d_fast = resolve_model_routing(strategy="fastest", default_provider="gemini", default_model="gemini-2.5-flash")
    assert d_fast.strategy == "fastest"
    assert d_fast.selected_model is not None

    # Highest quality strategy
    d_qual = resolve_model_routing(strategy="highest_quality", default_provider="gemini", default_model="gemini-2.5-flash")
    assert d_qual.strategy == "highest_quality"
    assert "gpt-4o" in d_qual.selected_model or "gemini-1.5-pro" in d_qual.selected_model

def test_repair_markdown_extraction():
    md_text = """Here is your extracted contact information:
```json
{
  "name": "Sarah Connor",
  "company": "Cyberdyne Systems",
  "phone": "+1-555-0199"
}
```
Hope this helps!"""
    block = extract_json_block(md_text)
    assert block is not None
    data = heuristic_json_fix(block)
    assert data["name"] == "Sarah Connor"
    assert data["company"] == "Cyberdyne Systems"

def test_repair_trailing_commas():
    bad_json = """{
      "title": "AI in 2026",
      "tags": ["tech", "future", ],
    }"""
    fixed = heuristic_json_fix(bad_json)
    assert fixed is not None
    assert fixed["title"] == "AI in 2026"
    assert fixed["tags"] == ["tech", "future"]
