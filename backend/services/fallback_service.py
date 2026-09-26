from typing import Optional, List, Tuple
from pydantic import BaseModel
from backend.services.providers.base import AIProvider, ProviderResult, ImagePayload, FilePayload
from backend.services.providers.registry import provider_registry

class FallbackExecutionReport(BaseModel):
    fallback_used: bool = False
    primary_provider: str
    primary_model: str
    primary_error: Optional[str] = None
    fallback_provider: Optional[str] = None
    fallback_model: Optional[str] = None
    result: Optional[ProviderResult] = None

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
    temperature: float = 0.1
) -> FallbackExecutionReport:
    primary_prov = provider_registry.get(provider_name)
    report = FallbackExecutionReport(
        fallback_used=False,
        primary_provider=provider_name,
        primary_model=model_id
    )

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
        return report

    except Exception as primary_exc:
        report.primary_error = str(primary_exc)

        # Check if fallback is configured and different
        can_fallback = (
            fallback_enabled
            and fallback_provider
            and fallback_model
            and not (fallback_provider.lower() == provider_name.lower() and fallback_model == model_id)
        )

        if not can_fallback:
            raise primary_exc

        report.fallback_used = True
        report.fallback_provider = fallback_provider
        report.fallback_model = fallback_model

        try:
            fb_prov = provider_registry.get(fallback_provider)
            fb_res = await fb_prov.generate(
                model_id=fallback_model,
                prompt=prompt,
                system_prompt=system_prompt,
                json_schema=json_schema,
                images=images,
                files=files,
                temperature=temperature
            )
            report.result = fb_res
            return report
        except Exception as fb_exc:
            raise RuntimeError(
                f"Both primary ({provider_name}/{model_id}: {primary_exc}) and fallback "
                f"({fallback_provider}/{fallback_model}: {fb_exc}) failed."
            )
