from typing import Optional
from pydantic import BaseModel

class ModelInfo(BaseModel):
    provider: str
    model_id: str
    display_name: str
    supports_text: bool = True
    supports_vision: bool = False
    supports_json: bool = True
    input_cost_per_m: float  # USD per 1M input tokens
    output_cost_per_m: float # USD per 1M output tokens
    quality_score: float     # 1-100 estimate
    speed_score: float       # 1-100 estimate
    is_enabled: bool = True

DEFAULT_MODEL_CATALOG: list[ModelInfo] = [
    ModelInfo(
        provider="gemini",
        model_id="gemini-2.5-flash",
        display_name="Gemini 2.5 Flash",
        supports_text=True,
        supports_vision=True,
        supports_json=True,
        input_cost_per_m=0.15,
        output_cost_per_m=0.60,
        quality_score=90.0,
        speed_score=95.0,
        is_enabled=True
    ),
    ModelInfo(
        provider="gemini",
        model_id="gemini-1.5-flash",
        display_name="Gemini 1.5 Flash",
        supports_text=True,
        supports_vision=True,
        supports_json=True,
        input_cost_per_m=0.075,
        output_cost_per_m=0.30,
        quality_score=85.0,
        speed_score=94.0,
        is_enabled=True
    ),
    ModelInfo(
        provider="gemini",
        model_id="gemini-1.5-pro",
        display_name="Gemini 1.5 Pro",
        supports_text=True,
        supports_vision=True,
        supports_json=True,
        input_cost_per_m=1.25,
        output_cost_per_m=5.00,
        quality_score=96.0,
        speed_score=78.0,
        is_enabled=True
    ),
    ModelInfo(
        provider="openai",
        model_id="gpt-4o-mini",
        display_name="OpenAI GPT-4o Mini",
        supports_text=True,
        supports_vision=True,
        supports_json=True,
        input_cost_per_m=0.15,
        output_cost_per_m=0.60,
        quality_score=88.0,
        speed_score=92.0,
        is_enabled=True
    ),
    ModelInfo(
        provider="openai",
        model_id="gpt-4o",
        display_name="OpenAI GPT-4o",
        supports_text=True,
        supports_vision=True,
        supports_json=True,
        input_cost_per_m=2.50,
        output_cost_per_m=10.00,
        quality_score=97.0,
        speed_score=82.0,
        is_enabled=True
    ),
    ModelInfo(
        provider="groq",
        model_id="llama-3.3-70b-versatile",
        display_name="Groq Llama 3.3 70B",
        supports_text=True,
        supports_vision=False,
        supports_json=True,
        input_cost_per_m=0.59,
        output_cost_per_m=0.79,
        quality_score=89.0,
        speed_score=98.0,
        is_enabled=True
    ),
    ModelInfo(
        provider="groq",
        model_id="llama-3.2-11b-vision-preview",
        display_name="Groq Llama 3.2 11B Vision",
        supports_text=True,
        supports_vision=True,
        supports_json=True,
        input_cost_per_m=0.18,
        output_cost_per_m=0.18,
        quality_score=83.0,
        speed_score=96.0,
        is_enabled=True
    )
]

def calculate_request_cost(model_id: str, input_tokens: int, output_tokens: int) -> float:
    """Calculates estimated request cost in USD."""
    match = next((m for m in DEFAULT_MODEL_CATALOG if m.model_id == model_id), None)
    if not match:
        # Fallback heuristic: $0.20 per 1M tokens
        return round(((input_tokens + output_tokens) / 1_000_000.0) * 0.20, 6)

    in_cost = (input_tokens / 1_000_000.0) * match.input_cost_per_m
    out_cost = (output_tokens / 1_000_000.0) * match.output_cost_per_m
    return round(in_cost + out_cost, 6)
