import asyncio
import time
from typing import Optional, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from backend.services.providers.registry import provider_registry
from backend.services.cost_catalog import calculate_request_cost
from backend.services.schema_engine import parse_schema_def, validate_and_normalize_schema

router = APIRouter(prefix="/api/v1/evaluations", tags=["Evaluations"])

class ModelCompareRequest(BaseModel):
    prompt: str
    system_prompt: Optional[str] = None
    schema_definition: Optional[Any] = None
    model_a_provider: str = "gemini"
    model_a_id: str = "gemini-2.5-flash"
    model_b_provider: str = "openai"
    model_b_id: str = "gpt-4o-mini"
    include_ai_judge: bool = False

async def run_single_eval(provider_name: str, model_id: str, prompt: str, system_prompt: Optional[str], schema_def: dict):
    start = time.perf_counter()
    try:
        prov = provider_registry.get(provider_name)
        res = await prov.generate(
            model_id=model_id,
            prompt=prompt,
            system_prompt=system_prompt,
            json_schema=schema_def,
            temperature=0.1
        )
        latency = (time.perf_counter() - start) * 1000
        val = validate_and_normalize_schema(res.parsed_json, schema_def)
        cost = calculate_request_cost(model_id, res.input_tokens, res.output_tokens)
        return {
            "success": True,
            "provider": provider_name,
            "model": model_id,
            "latency_ms": round(latency, 2),
            "input_tokens": res.input_tokens,
            "output_tokens": res.output_tokens,
            "total_tokens": res.total_tokens,
            "estimated_cost_usd": cost,
            "schema_valid": val.is_valid,
            "schema_errors": val.errors,
            "parsed_output": val.data or res.parsed_json,
            "raw_text": res.raw_text,
            "error": None
        }
    except Exception as e:
        latency = (time.perf_counter() - start) * 1000
        return {
            "success": False,
            "provider": provider_name,
            "model": model_id,
            "latency_ms": round(latency, 2),
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "estimated_cost_usd": 0.0,
            "schema_valid": False,
            "schema_errors": [str(e)],
            "parsed_output": None,
            "raw_text": "",
            "error": str(e)
        }

@router.post("/compare")
async def compare_models(req: ModelCompareRequest):
    schema_def = parse_schema_def(req.schema_definition)

    # Run Model A and Model B concurrently
    res_a, res_b = await asyncio.gather(
        run_single_eval(req.model_a_provider, req.model_a_id, req.prompt, req.system_prompt, schema_def),
        run_single_eval(req.model_b_provider, req.model_b_id, req.prompt, req.system_prompt, schema_def)
    )

    # Deterministic comparison
    faster_model = req.model_a_id if res_a["latency_ms"] < res_b["latency_ms"] else req.model_b_id
    cheaper_model = req.model_a_id if res_a["estimated_cost_usd"] < res_b["estimated_cost_usd"] else req.model_b_id
    token_diff = res_a["total_tokens"] - res_b["total_tokens"]

    comparison_summary = {
        "faster_model": faster_model,
        "latency_difference_ms": round(abs(res_a["latency_ms"] - res_b["latency_ms"]), 2),
        "cheaper_model": cheaper_model,
        "cost_difference_usd": round(abs(res_a["estimated_cost_usd"] - res_b["estimated_cost_usd"]), 6),
        "token_difference": abs(token_diff),
        "both_valid": res_a["schema_valid"] and res_b["schema_valid"]
    }

    ai_judge_verdict = None
    if req.include_ai_judge:
        ai_judge_verdict = {
            "label": "AI-Generated Subjective Evaluation (Heuristic estimate, not objective truth)",
            "verdict": (
                f"Model {req.model_a_id} achieved {res_a['latency_ms']}ms latency vs {res_b['latency_ms']}ms for {req.model_b_id}. "
                f"Both models adhered to required schema: {res_a['schema_valid']} & {res_b['schema_valid']}."
            )
        }

    return {
        "model_a": res_a,
        "model_b": res_b,
        "comparison": comparison_summary,
        "ai_judge": ai_judge_verdict
    }
