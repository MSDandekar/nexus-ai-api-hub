import hashlib
import secrets
from typing import Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from backend.models import ApiKey, utcnow
from backend.core.config import settings

def hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

def generate_api_key_pair(name: str) -> tuple[str, ApiKey]:
    """Generates a raw key (returned to user once) and ApiKey database entity with hash."""
    random_part = secrets.token_hex(20)
    raw_key = f"nx_live_{random_part}"
    prefix = raw_key[:12]
    hashed = hash_key(raw_key)

    api_key_entity = ApiKey(
        name=name,
        key_prefix=prefix,
        hashed_key=hashed,
        is_active=True
    )
    return raw_key, api_key_entity

async def verify_api_key(raw_key: Optional[str], db: AsyncSession) -> bool:
    if not raw_key:
        return False

    raw_key = raw_key.strip()
    if raw_key.startswith("Bearer "):
        raw_key = raw_key[7:].strip()

    # Master development / admin key check
    if settings.DEFAULT_ADMIN_API_KEY and raw_key == settings.DEFAULT_ADMIN_API_KEY:
        return True

    target_hash = hash_key(raw_key)
    query = select(ApiKey).where(ApiKey.hashed_key == target_hash, ApiKey.is_active == True)
    result = await db.execute(query)
    key_record = result.scalars().first()

    if key_record:
        # Update last used timestamp
        key_record.last_used_at = utcnow()
        await db.commit()
        return True

    return False
