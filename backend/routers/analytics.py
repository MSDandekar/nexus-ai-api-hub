from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
from backend.database import get_db
from backend.models import Connector, RequestLog

router = APIRouter(prefix="/api/v1/analytics", tags=["Analytics"])

@router.get("/dashboard")
async def get_dashboard_metrics(db: AsyncSession = Depends(get_db)):
    now = datetime.now(timezone.utc)
    start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start_of_week = start_of_today - timedelta(days=start_of_today.weekday())

    # 1. Connectors stats
    conn_total_res = await db.execute(select(func.count(Connector.id)))
    total_connectors = conn_total_res.scalar() or 0

    conn_active_res = await db.execute(select(func.count(Connector.id)).where(Connector.is_active == True))
    active_connectors = conn_active_res.scalar() or 0

    # 2. Total requests stats
    req_total_res = await db.execute(select(func.count(RequestLog.id)))
    total_requests = req_total_res.scalar() or 0

    success_res = await db.execute(select(func.count(RequestLog.id)).where(RequestLog.status.in_(["success", "repaired"])))
    success_requests = success_res.scalar() or 0

    fail_res = await db.execute(select(func.count(RequestLog.id)).where(RequestLog.status == "failure"))
    failed_requests = fail_res.scalar() or 0

    success_rate = round((success_requests / total_requests * 100), 1) if total_requests > 0 else 100.0
    failure_rate = round((failed_requests / total_requests * 100), 1) if total_requests > 0 else 0.0

    # 3. Latency & Tokens & Cost overall
    avg_latency_res = await db.execute(select(func.avg(RequestLog.response_time_ms)))
    avg_latency = round(avg_latency_res.scalar() or 0.0, 1)

    sum_cost_res = await db.execute(select(func.sum(RequestLog.estimated_cost)))
    total_cost = round(sum_cost_res.scalar() or 0.0, 5)

    sum_tokens_res = await db.execute(select(func.sum(RequestLog.total_tokens)))
    total_tokens = sum_tokens_res.scalar() or 0

    # 4. Cost Today & Cost This Week
    cost_today_res = await db.execute(
        select(func.sum(RequestLog.estimated_cost)).where(RequestLog.timestamp >= start_of_today)
    )
    cost_today = round(cost_today_res.scalar() or 0.0, 5)

    cost_week_res = await db.execute(
        select(func.sum(RequestLog.estimated_cost)).where(RequestLog.timestamp >= start_of_week)
    )
    cost_this_week = round(cost_week_res.scalar() or 0.0, 5)

    # 5. Cost & Requests by Provider
    prov_query = select(
        RequestLog.provider,
        func.count(RequestLog.id).label("requests"),
        func.sum(RequestLog.estimated_cost).label("cost")
    ).group_by(RequestLog.provider)
    prov_res = await db.execute(prov_query)
    by_provider = [
        {"provider": row[0], "requests": row[1], "cost": round(row[2] or 0.0, 5)}
        for row in prov_res.all()
    ]

    # 6. Cost & Requests by Connector
    conn_cost_query = select(
        RequestLog.connector_slug,
        func.count(RequestLog.id).label("requests"),
        func.sum(RequestLog.estimated_cost).label("cost"),
        func.avg(RequestLog.response_time_ms).label("avg_latency")
    ).group_by(RequestLog.connector_slug)
    conn_cost_res = await db.execute(conn_cost_query)
    by_connector = [
        {
            "connector_slug": row[0],
            "requests": row[1],
            "cost": round(row[2] or 0.0, 5),
            "avg_latency": round(row[3] or 0.0, 1)
        }
        for row in conn_cost_res.all()
    ]

    # 7. Daily Trend (last 7 days)
    seven_days_ago = start_of_today - timedelta(days=6)
    daily_query = select(
        func.date(RequestLog.timestamp).label("day"),
        func.count(RequestLog.id).label("requests"),
        func.sum(RequestLog.estimated_cost).label("cost")
    ).where(RequestLog.timestamp >= seven_days_ago).group_by(func.date(RequestLog.timestamp)).order_by("day")
    daily_res = await db.execute(daily_query)
    daily_trend = [
        {"date": str(row[0]), "requests": row[1], "cost": round(row[2] or 0.0, 5)}
        for row in daily_res.all()
    ]

    return {
        "overview": {
            "total_connectors": total_connectors,
            "active_connectors": active_connectors,
            "total_requests": total_requests,
            "success_rate": success_rate,
            "failure_rate": failure_rate,
            "avg_latency_ms": avg_latency,
            "total_tokens": total_tokens,
            "total_cost_usd": total_cost,
            "cost_today_usd": cost_today,
            "cost_this_week_usd": cost_this_week,
        },
        "by_provider": by_provider,
        "by_connector": by_connector,
        "daily_trend": daily_trend
    }

@router.get("/logs")
async def get_request_logs(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    connector: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    query = select(RequestLog).order_by(desc(RequestLog.timestamp))
    conditions = []
    if connector:
        conditions.append(RequestLog.connector_slug == connector)
    if status:
        conditions.append(RequestLog.status == status)

    if conditions:
        query = query.where(and_(*conditions))

    total_query = select(func.count(RequestLog.id))
    if conditions:
        total_query = total_query.where(and_(*conditions))

    total_res = await db.execute(total_query)
    total_count = total_res.scalar() or 0

    query = query.offset(offset).limit(limit)
    res = await db.execute(query)
    logs = res.scalars().all()

    items = []
    for l in logs:
        items.append({
            "id": l.id,
            "request_id": l.request_id,
            "connector_slug": l.connector_slug,
            "timestamp": l.timestamp.isoformat() if l.timestamp else None,
            "provider": l.provider,
            "model": l.model,
            "status": l.status,
            "response_time_ms": l.response_time_ms,
            "tokens": {
                "input": l.input_tokens,
                "output": l.output_tokens,
                "total": l.total_tokens
            },
            "estimated_cost_usd": l.estimated_cost,
            "routing_strategy": l.routing_strategy,
            "routing_reason": l.routing_reason,
            "fallback_used": l.fallback_used,
            "fallback_provider": l.fallback_provider,
            "fallback_model": l.fallback_model,
            "repair_attempted": l.repair_attempted,
            "error_code": l.error_code,
            "error_message": l.error_message,
            "request_payload": l.request_payload,
            "response_payload": l.response_payload
        })

    return {"logs": items, "total": total_count, "limit": limit, "offset": offset}
