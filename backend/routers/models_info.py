from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.database import get_db
from backend.models import ModelCatalogEntry
from backend.services.providers.registry import provider_registry
from backend.services.cost_catalog import DEFAULT_MODEL_CATALOG

router = APIRouter(prefix="/api/v1/models", tags=["Models"])

@router.get("")
async def list_models(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(ModelCatalogEntry).where(ModelCatalogEntry.is_enabled == True))
    entries = res.scalars().all()
    if not entries:
        entries = DEFAULT_MODEL_CATALOG

    return {
        "models": [
            {
                "provider": m.provider,
                "model_id": m.model_id,
                "display_name": m.display_name,
                "supports_text": m.supports_text,
                "supports_vision": m.supports_vision,
                "supports_json": m.supports_json,
                "input_cost_per_m": m.input_cost_per_m,
                "output_cost_per_m": m.output_cost_per_m,
                "quality_score": m.quality_score,
                "speed_score": m.speed_score
            }
            for m in entries
        ],
        "providers": provider_registry.list_providers()
    }
