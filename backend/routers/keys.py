from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from backend.database import get_db
from backend.models import ApiKey
from backend.services.auth import generate_api_key_pair

router = APIRouter(prefix="/api/v1/keys", tags=["API Keys"])

class KeyCreateDTO(BaseModel):
    name: str

@router.get("")
async def list_keys(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(ApiKey).order_by(desc(ApiKey.created_at)))
    keys = res.scalars().all()
    return {
        "keys": [
            {
                "id": k.id,
                "name": k.name,
                "key_prefix": k.key_prefix,
                "is_active": k.is_active,
                "created_at": k.created_at.isoformat() if k.created_at else None,
                "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
            }
            for k in keys
        ]
    }

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_key(dto: KeyCreateDTO, db: AsyncSession = Depends(get_db)):
    raw_key, entity = generate_api_key_pair(dto.name)
    db.add(entity)
    await db.commit()
    await db.refresh(entity)

    # raw_key is returned ONLY here upon creation
    return {
        "message": "API key generated successfully. Copy it now, as it cannot be shown again.",
        "api_key": raw_key,
        "key_prefix": entity.key_prefix,
        "name": entity.name,
        "id": entity.id
    }

@router.patch("/{key_id}/toggle")
async def toggle_key(key_id: int, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(ApiKey).where(ApiKey.id == key_id))
    key = res.scalars().first()
    if not key:
        raise HTTPException(status_code=404, detail="API Key not found")
    key.is_active = not key.is_active
    await db.commit()
    return {"id": key.id, "is_active": key.is_active}

@router.delete("/{key_id}")
async def delete_key(key_id: int, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(ApiKey).where(ApiKey.id == key_id))
    key = res.scalars().first()
    if not key:
        raise HTTPException(status_code=404, detail="API Key not found")
    await db.delete(key)
    await db.commit()
    return {"message": "API Key deleted"}
