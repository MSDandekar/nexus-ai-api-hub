import logging
import json
from typing import Optional, Any
from datetime import datetime, timezone
import secrets
from sqlalchemy.ext.asyncio import AsyncSession
from backend.models import RequestLog, utcnow

logger = logging.getLogger("ai_nexus.logger")

def generate_request_id() -> str:
    today_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    hex_suffix = secrets.token_hex(3).upper()
    return f"REQ-{today_str}-{hex_suffix}"

async def log_request_event(
    db: AsyncSession,
    request_id: str,
    connector_id: Optional[int],
    connector_slug: str,
    provider: str,
    model: str,
    status: str,
    response_time_ms: float,
    input_tokens: int = 0,
    output_tokens: int = 0,
    total_tokens: int = 0,
    estimated_cost: float = 0.0,
    routing_strategy: Optional[str] = None,
    routing_reason: Optional[str] = None,
    fallback_used: bool = False,
    fallback_provider: Optional[str] = None,
    fallback_model: Optional[str] = None,
    repair_attempted: bool = False,
    error_code: Optional[str] = None,
    error_message: Optional[str] = None,
    request_payload: Optional[Any] = None,
    response_payload: Optional[Any] = None,
) -> Optional[RequestLog]:
    """Safely writes persistent request log. Fails gracefully without throwing."""
    try:
        def sanitize_payload(payload: Any) -> Optional[str]:
            if payload is None:
                return None
            try:
                # If dict/list, serialize; limit to 4000 characters
                s = json.dumps(payload, default=str)
                return s[:4000]
            except Exception:
                return str(payload)[:4000]

        log_entry = RequestLog(
            request_id=request_id,
            connector_id=connector_id,
            connector_slug=connector_slug,
            timestamp=utcnow(),
            provider=provider,
            model=model,
            status=status,
            response_time_ms=response_time_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            estimated_cost=estimated_cost,
            routing_strategy=routing_strategy,
            routing_reason=routing_reason,
            fallback_used=fallback_used,
            fallback_provider=fallback_provider,
            fallback_model=fallback_model,
            repair_attempted=repair_attempted,
            error_code=error_code,
            error_message=error_message,
            request_payload=sanitize_payload(request_payload),
            response_payload=sanitize_payload(response_payload)
        )
        db.add(log_entry)
        await db.commit()
        return log_entry
    except Exception as e:
        logger.error(f"Failed to record request log for {request_id}: {e}")
        try:
            await db.rollback()
        except Exception:
            pass
        return None
