from typing import Optional, List
from pydantic import BaseModel
from backend.services.cost_catalog import DEFAULT_MODEL_CATALOG, ModelInfo
from backend.services.providers.registry import provider_registry

class RoutingDecision(BaseModel):
    strategy: str
    task_type: str
    selected_provider: str
    selected_model: str
    reason: str
    candidate_count: int

def determine_task_type(has_images: bool, has_files: bool, has_schema: bool, prompt_len: int) -> str:
    if has_images:
        return "vision"
    if has_files:
        return "multimodal_document"
    if has_schema:
        return "structured_extraction"
    if prompt_len > 4000:
        return "long_context"
    return "general_text"

def resolve_model_routing(
    strategy: str,
    default_provider: str,
    default_model: str,
    has_images: bool = False,
    has_files: bool = False,
    has_schema: bool = False,
    prompt_len: int = 0,
    catalog: Optional[List[ModelInfo]] = None
) -> RoutingDecision:
    strategy = (strategy or "specific").lower()
    task_type = determine_task_type(has_images, has_files, has_schema, prompt_len)
    models = catalog or DEFAULT_MODEL_CATALOG

    # Filter enabled models
    candidates = [m for m in models if m.is_enabled]

    # Modality filtering
    if has_images:
        candidates = [m for m in candidates if m.supports_vision]

    if strategy == "specific" or not candidates:
        reason = f"Explicitly configured model '{default_model}' via provider '{default_provider}'."
        return RoutingDecision(
            strategy="specific",
            task_type=task_type,
            selected_provider=default_provider,
            selected_model=default_model,
            reason=reason,
            candidate_count=1
        )

    if strategy == "cheapest":
        # Sort by avg cost per million tokens
        candidates.sort(key=lambda m: (m.input_cost_per_m + m.output_cost_per_m))
        selected = candidates[0]
        avg_cost = (selected.input_cost_per_m + selected.output_cost_per_m) / 2
        reason = f"Lowest blended token cost (${avg_cost:.3f}/1M) among {len(candidates)} compatible models."

    elif strategy == "fastest":
        candidates.sort(key=lambda m: m.speed_score, reverse=True)
        selected = candidates[0]
        reason = f"Highest configured throughput/speed index ({selected.speed_score}/100) for task type '{task_type}'."

    elif strategy == "highest_quality":
        candidates.sort(key=lambda m: m.quality_score, reverse=True)
        selected = candidates[0]
        reason = f"Highest configured reasoning & accuracy index ({selected.quality_score}/100) for task type '{task_type}'."

    elif strategy in ("balanced", "auto"):
        # Max-min normalization for cost to build composite balanced score
        max_cost = max((m.input_cost_per_m + m.output_cost_per_m) for m in candidates) or 1.0
        
        def score(m: ModelInfo) -> float:
            cost_factor = ((m.input_cost_per_m + m.output_cost_per_m) / max_cost) * 100.0
            # Higher quality (40%), higher speed (35%), lower cost (25%)
            return (m.quality_score * 0.40) + (m.speed_score * 0.35) - (cost_factor * 0.25)

        candidates.sort(key=score, reverse=True)
        selected = candidates[0]
        reason = (
            f"{strategy.capitalize()} selection: Task '{task_type}' matched with {selected.display_name} "
            f"(Quality: {selected.quality_score:.0f}, Speed: {selected.speed_score:.0f}, "
            f"Input: ${selected.input_cost_per_m}/M, Output: ${selected.output_cost_per_m}/M)."
        )
    else:
        selected = candidates[0]
        reason = f"Default routing fallback to {selected.model_id}."

    return RoutingDecision(
        strategy=strategy,
        task_type=task_type,
        selected_provider=selected.provider,
        selected_model=selected.model_id,
        reason=reason,
        candidate_count=len(candidates)
    )
