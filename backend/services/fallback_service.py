import re
from typing import Optional, List, Tuple
from pydantic import BaseModel
from backend.services.providers.base import (
    AIProvider, ProviderResult, ImagePayload, FilePayload,
    ProviderException, ProviderErrorKind, classify_provider_error
)
from backend.services.providers.registry import provider_registry
from backend.services.cost_catalog import DEFAULT_MODEL_CATALOG, ModelInfo

class FallbackExecutionReport(BaseModel):
    fallback_used: bool = False
    primary_provider: str
    primary_model: str
    primary_error: Optional[str] = None
    fallback_provider: Optional[str] = None
    fallback_model: Optional[str] = None
    result: Optional[ProviderResult] = None

def build_fallback_candidates(
    primary_provider: str,
    primary_model: str,
    is_provider_level_error: bool,
    has_images: bool,
    has_files: bool,
    has_schema: bool,
    configured_fallback_provider: Optional[str] = None,
    configured_fallback_model: Optional[str] = None,
    routing_strategy: str = "balanced"
) -> List[Tuple[str, str]]:
    """
    Intelligently discovers eligible fallback models matching capabilities,
    configured credentials, and modality requirements without hardcoding provider pairs.
    """
    eligible: List[ModelInfo] = []
    failed_prov_lower = primary_provider.lower()

    for m in DEFAULT_MODEL_CATALOG:
        if not m.is_enabled:
            continue

        # Cannot fallback to the exact same model
        if m.provider.lower() == failed_prov_lower and m.model_id == primary_model:
            continue

        # If primary failed with account-wide quota or auth error, do not retry same provider
        if is_provider_level_error and m.provider.lower() == failed_prov_lower:
            continue

        prov = provider_registry.get(m.provider)
        if not prov or not prov.is_configured():
            continue

        # Modality checks
        if has_images and not (prov.supports_vision(m.model_id) and m.supports_vision):
            continue
        if has_schema and not (prov.supports_json(m.model_id) and m.supports_json):
            continue

        eligible.append(m)

    if not eligible:
        return []

    # Sort based on routing strategy
    strategy = (routing_strategy or "balanced").lower()
    if strategy == "cheapest":
        eligible.sort(key=lambda m: (m.input_cost_per_m + m.output_cost_per_m))
    elif strategy == "fastest":
        eligible.sort(key=lambda m: m.speed_score, reverse=True)
    elif strategy == "highest_quality":
        eligible.sort(key=lambda m: m.quality_score, reverse=True)
    else:
        # Balanced score
        max_cost = max((m.input_cost_per_m + m.output_cost_per_m) for m in eligible) or 1.0
        def score(m: ModelInfo) -> float:
            cost_factor = ((m.input_cost_per_m + m.output_cost_per_m) / max_cost) * 100.0
            return (m.quality_score * 0.40) + (m.speed_score * 0.35) - (cost_factor * 0.25)
        eligible.sort(key=score, reverse=True)

    candidates: List[Tuple[str, str]] = []

    # If connector has an explicitly configured fallback that matches eligibility, prioritize it
    if configured_fallback_provider and configured_fallback_model:
        cf_prov = configured_fallback_provider.lower()
        cf_mod = configured_fallback_model
        # Check if configured fallback is eligible
        if any(m.provider.lower() == cf_prov and m.model_id == cf_mod for m in eligible):
            candidates.append((configured_fallback_provider, configured_fallback_model))

    for m in eligible:
        pair = (m.provider, m.model_id)
        if pair not in candidates:
            candidates.append(pair)

    return candidates

async def execute_with_fallback(
    provider_name: str,
    model_id: str,
    prompt: str,
    system_prompt: Optional[str] = None,
    json_schema: Optional[dict] = None,
    images: Optional[List[ImagePayload]] = None,
    files: Optional[List[FilePayload]] = None,
    fallback_enabled: bool = False,
    fallback_provider: Optional[str] = None,
    fallback_model: Optional[str] = None,
    temperature: float = 0.1,
    routing_strategy: str = "balanced",
    trace: Optional[List[dict]] = None
) -> FallbackExecutionReport:
    """
    Executes primary model with intelligent, provider-aware cross-provider fallback.
    Prevents blind same-provider retries on 429 quota exhaustion or auth errors.
    """
    primary_prov = provider_registry.get(provider_name)
    report = FallbackExecutionReport(
        fallback_used=False,
        primary_provider=provider_name,
        primary_model=model_id
    )

    has_images = bool(images and len(images) > 0)
    has_files = bool(files and len(files) > 0)
    has_schema = bool(json_schema)

    # 1. Attempt Primary Execution
    try:
        res = await primary_prov.generate(
            model_id=model_id,
            prompt=prompt,
            system_prompt=system_prompt,
            json_schema=json_schema,
            images=images,
            files=files,
            temperature=temperature
        )
        report.result = res
        if trace is not None:
            trace.append({
                "step": "AI Inference",
                "status": "ok",
                "detail": f"Completed via {res.provider}/{res.model} in {res.latency_ms}ms"
            })
        return report

    except Exception as primary_exc:
        # Wrap in ProviderException if raw exception
        if isinstance(primary_exc, ProviderException):
            p_err = primary_exc
        else:
            kind, msg = classify_provider_error(provider_name, getattr(primary_exc, "status_code", None), str(primary_exc))
            p_err = ProviderException(error_kind=kind, message=msg, provider=provider_name, raw_error=str(primary_exc))

        report.primary_error = p_err.message
        is_provider_level = p_err.is_provider_level()

        # Trace primary failure
        if trace is not None:
            reason_text = "quota exceeded (HTTP 429)" if p_err.error_kind == ProviderErrorKind.QUOTA_EXCEEDED else p_err.message
            trace.append({
                "step": "AI Inference",
                "status": "warning",
                "detail": f"{primary_provider_title(provider_name)} {reason_text}. Attempting cross-provider fallback."
            })

        if not fallback_enabled:
            raise p_err

        # 2. Build candidate fallback models
        candidates = build_fallback_candidates(
            primary_provider=provider_name,
            primary_model=model_id,
            is_provider_level_error=is_provider_level,
            has_images=has_images,
            has_files=has_files,
            has_schema=has_schema,
            configured_fallback_provider=fallback_provider,
            configured_fallback_model=fallback_model,
            routing_strategy=routing_strategy
        )

        if not candidates:
            if p_err.error_kind == ProviderErrorKind.QUOTA_EXCEEDED:
                raise ProviderException(
                    error_kind=ProviderErrorKind.QUOTA_EXCEEDED,
                    message="AI provider quota or availability limit reached. No configured fallback provider was available. Please try again later or configure another provider.",
                    provider=provider_name
                )
            raise p_err

        # 3. Iterate through fallback candidates
        exhausted_providers = {provider_name.lower()} if is_provider_level else set()
        fallback_errors = []
        attempted_fallbacks: List[Tuple[str, str, ProviderException]] = []

        for fb_prov_name, fb_mod_id in candidates:
            if fb_prov_name.lower() in exhausted_providers:
                continue

            if trace is not None:
                trace.append({
                    "step": "Fallback",
                    "status": "ok",
                    "detail": f"Fallback selected: {fb_prov_name}/{fb_mod_id}"
                })

            try:
                fb_prov = provider_registry.get(fb_prov_name)
                fb_res = await fb_prov.generate(
                    model_id=fb_mod_id,
                    prompt=prompt,
                    system_prompt=system_prompt,
                    json_schema=json_schema,
                    images=images,
                    files=files,
                    temperature=temperature
                )
                if trace is not None:
                    trace.append({
                        "step": "AI Inference",
                        "status": "ok",
                        "detail": f"Completed via {fb_res.provider}/{fb_res.model} in {fb_res.latency_ms}ms"
                    })

                report.fallback_used = True
                report.fallback_provider = fb_prov_name
                report.fallback_model = fb_mod_id
                report.result = fb_res
                return report

            except Exception as fb_exc:
                if isinstance(fb_exc, ProviderException):
                    fb_p_err = fb_exc
                else:
                    fb_kind, fb_msg = classify_provider_error(fb_prov_name, getattr(fb_exc, "status_code", None), str(fb_exc))
                    fb_p_err = ProviderException(error_kind=fb_kind, message=fb_msg, provider=fb_prov_name, raw_error=str(fb_exc))

                if fb_p_err.is_provider_level():
                    exhausted_providers.add(fb_prov_name.lower())

                attempted_fallbacks.append((fb_prov_name, fb_mod_id, fb_p_err))
                fallback_errors.append(f"{fb_prov_name}/{fb_mod_id}: {fb_p_err.message}")

                if trace is not None:
                    reason_desc = "quota exceeded (HTTP 429)" if fb_p_err.error_kind == ProviderErrorKind.QUOTA_EXCEEDED else fb_p_err.message
                    trace.append({
                        "step": "Fallback Inference",
                        "status": "failed",
                        "detail": f"{primary_provider_title(fb_prov_name)} fallback failed ({fb_p_err.error_kind.value}): {reason_desc}"
                    })

        # If one or more fallback providers were attempted and failed, preserve the actual fallback failure
        if attempted_fallbacks:
            last_prov, last_mod, last_err = attempted_fallbacks[-1]
            if last_err.error_kind == ProviderErrorKind.QUOTA_EXCEEDED:
                raise ProviderException(
                    error_kind=ProviderErrorKind.QUOTA_EXCEEDED,
                    message=f"{primary_provider_title(last_prov)} quota exceeded (HTTP 429). Please retry later or use another configured provider.",
                    provider=last_prov,
                    status_code=last_err.status_code,
                    raw_error=last_err.raw_error
                )
            elif last_err.error_kind == ProviderErrorKind.AUTHENTICATION_ERROR:
                raise ProviderException(
                    error_kind=ProviderErrorKind.AUTHENTICATION_ERROR,
                    message=f"{primary_provider_title(last_prov)} authentication failed. Please verify API key configuration.",
                    provider=last_prov,
                    status_code=last_err.status_code,
                    raw_error=last_err.raw_error
                )
            else:
                raise last_err

        # If NO fallback candidates could be attempted
        if p_err.error_kind == ProviderErrorKind.QUOTA_EXCEEDED:
            raise ProviderException(
                error_kind=ProviderErrorKind.QUOTA_EXCEEDED,
                message="AI provider quota or availability limit reached. No configured fallback provider was available. Please try again later or configure another provider.",
                provider="gateway"
            )

        raise ProviderException(
            error_kind=ProviderErrorKind.PROVIDER_ERROR,
            message="AI provider quota or availability limit reached. No configured fallback provider was available. Please try again later or configure another provider.",
            provider="gateway"
        )

def primary_provider_title(prov_name: str) -> str:
    name_map = {"gemini": "Gemini", "openai": "OpenAI", "groq": "Groq"}
    return name_map.get(prov_name.lower(), prov_name.capitalize())

