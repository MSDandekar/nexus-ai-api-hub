import json
import re
from typing import Optional
from pydantic import BaseModel
from backend.services.providers.registry import provider_registry
from backend.services.cost_catalog import DEFAULT_MODEL_CATALOG

class BlueprintProposal(BaseModel):
    name: str
    slug: str
    description: str
    provider: str
    model_id: str
    system_prompt: str
    routing_strategy: str = "balanced"
    fallback_enabled: bool = True
    inputs: list[dict]
    schema_definition: dict

HEURISTIC_TEMPLATES = [
    {
        "keywords": ["support", "email", "ticket", "customer"],
        "name": "Customer Support Email Extractor",
        "slug": "support-ticket-extractor",
        "description": "Extracts customer identity, sentiment, urgency, and core inquiry from incoming customer support emails.",
        "provider": "gemini",
        "model_id": "gemini-2.5-flash",
        "system_prompt": "You are a customer service AI. Extract customer information, inquiry details, sentiment, and required action items from the provided support message.",
        "inputs": [
            {"name": "email_body", "type": "text", "is_required": True, "description": "Full raw text of the customer email", "default_value": ""},
            {"name": "sender_email", "type": "text", "is_required": False, "description": "Sender email address if available", "default_value": ""}
        ],
        "schema_definition": {
            "customer_name": "string",
            "sentiment": "string",
            "urgency": "string",
            "issue_category": "string",
            "summary": "string",
            "recommended_action": "string"
        }
    },
    {
        "keywords": ["receipt", "invoice", "expense", "bill"],
        "name": "Invoice & Receipt Parser",
        "slug": "invoice-receipt-parser",
        "description": "Parses scanned receipts or PDF bills to extract vendor, line items, taxes, and total amounts.",
        "provider": "gemini",
        "model_id": "gemini-2.5-flash",
        "system_prompt": "You are a specialized financial document parser. Extract all vendor details, billing dates, line items, and financial totals from the image.",
        "inputs": [
            {"name": "image", "type": "image", "is_required": True, "description": "Receipt or invoice image file", "default_value": ""},
            {"name": "currency_hint", "type": "text", "is_required": False, "description": "Expected currency (USD, EUR, INR, etc.)", "default_value": "USD"}
        ],
        "schema_definition": {
            "vendor_name": "string",
            "invoice_number": "string",
            "date": "string",
            "subtotal": "number",
            "tax_amount": "number",
            "total_amount": "number",
            "currency": "string"
        }
    },
    {
        "keywords": ["translate", "language", "localization"],
        "name": "Intelligent Multi-Language Translator",
        "slug": "intelligent-translator",
        "description": "Translates text into target languages while preserving tone, nuance, and terminology.",
        "provider": "openai",
        "model_id": "gpt-4o-mini",
        "system_prompt": "You are a professional localization and translation engine. Translate the provided text into the target language accurately.",
        "inputs": [
            {"name": "text", "type": "text", "is_required": True, "description": "Source text to translate", "default_value": ""},
            {"name": "target_language", "type": "text", "is_required": True, "description": "Target language (e.g. Spanish, French, Japanese)", "default_value": "Spanish"}
        ],
        "schema_definition": {
            "source_language": "string",
            "target_language": "string",
            "translated_text": "string",
            "tone_analysis": "string"
        }
    }
]

async def generate_blueprint(user_prompt: str) -> BlueprintProposal:
    """Generates a complete connector configuration blueprint from a natural language description."""
    user_prompt_lower = user_prompt.lower()

    # Try AI generation first if Gemini or OpenAI is configured
    for p_name in ["gemini", "openai", "groq"]:
        try:
            prov = provider_registry.get(p_name)
            if prov.is_configured():
                default_model = "gemini-2.5-flash" if p_name == "gemini" else "gpt-4o-mini"
                ai_prompt = f"""
You are an expert API architect for 'AI Nexus'. An admin wants to create a new AI API Connector with this description:
"{user_prompt}"

Generate a complete, production-ready connector blueprint. Respond ONLY with valid JSON matching this schema:
{{
  "name": "Human-readable Connector Name",
  "slug": "url-friendly-kebab-slug",
  "description": "Comprehensive explanation of what this connector does",
  "provider": "{p_name}",
  "model_id": "{default_model}",
  "system_prompt": "Precise system prompt instructions for the AI",
  "routing_strategy": "balanced",
  "fallback_enabled": true,
  "inputs": [
    {{"name": "param_name", "type": "text|number|boolean|image|file|json", "is_required": true, "description": "param explanation", "default_value": ""}}
  ],
  "schema_definition": {{
    "field1": "string",
    "field2": "number",
    "field3": "string"
  }}
}}
"""
                res = await prov.generate(
                    model_id=default_model,
                    prompt=ai_prompt,
                    temperature=0.2
                )
                if res.parsed_json and isinstance(res.parsed_json, dict):
                    pj = res.parsed_json
                    return BlueprintProposal(
                        name=pj.get("name", "Generated Connector"),
                        slug=re.sub(r'[^a-z0-9-]', '', pj.get("slug", "new-connector").lower().replace(' ', '-')),
                        description=pj.get("description", user_prompt),
                        provider=pj.get("provider", p_name),
                        model_id=pj.get("model_id", default_model),
                        system_prompt=pj.get("system_prompt", "Process input data."),
                        routing_strategy=pj.get("routing_strategy", "balanced"),
                        fallback_enabled=pj.get("fallback_enabled", True),
                        inputs=pj.get("inputs", [{"name": "input_text", "type": "text", "is_required": True}]),
                        schema_definition=pj.get("schema_definition", {"result": "string"})
                    )
        except Exception:
            pass

    # Heuristic match
    for template in HEURISTIC_TEMPLATES:
        if any(kw in user_prompt_lower for kw in template["keywords"]):
            return BlueprintProposal(
                name=template["name"],
                slug=template["slug"],
                description=template["description"],
                provider=template["provider"],
                model_id=template["model_id"],
                system_prompt=template["system_prompt"],
                routing_strategy="balanced",
                fallback_enabled=True,
                inputs=template["inputs"],
                schema_definition=template["schema_definition"]
            )

    # General fallback proposal
    cleaned_slug = re.sub(r'[^a-z0-9-]', '', user_prompt_lower[:25].replace(' ', '-')) or "custom-connector"
    return BlueprintProposal(
        name=user_prompt[:40].title() if user_prompt else "Custom API Connector",
        slug=cleaned_slug,
        description=user_prompt or "Custom intelligent API connector",
        provider="gemini",
        model_id="gemini-2.5-flash",
        system_prompt=f"You are a specialized AI processor. Analyze the input carefully and provide structured extraction according to the schema.",
        routing_strategy="balanced",
        fallback_enabled=True,
        inputs=[
            {"name": "input_content", "type": "text", "is_required": True, "description": "The primary input text or query", "default_value": ""}
        ],
        schema_definition={
            "summary": "string",
            "confidence_score": "number",
            "key_attributes": "array",
            "status": "string"
        }
    )
