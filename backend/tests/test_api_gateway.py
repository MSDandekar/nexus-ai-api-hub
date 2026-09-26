import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch

from backend.main import app
from backend.seed import seed_database
from backend.services.providers.base import ProviderResult
from backend.services.providers.registry import provider_registry

@pytest_asyncio.fixture(autouse=True)
async def init_db():
    await seed_database()

@pytest.mark.asyncio
async def test_health_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["database"] == "ok"

@pytest.mark.asyncio
async def test_gateway_unauthorized():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/v1/run/card-scanner", json={})
        assert resp.status_code == 401
        data = resp.json()
        assert data["success"] is False
        assert data["error"]["code"] == "UNAUTHORIZED"

@pytest.mark.asyncio
async def test_gateway_validation_failure():
    transport = ASGITransport(app=app)
    headers = {"X-API-Key": "nexus-dev-master-key-2026"}
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Article intelligence requires article_text min length 20
        resp = await client.post(
            "/api/v1/run/article-intelligence",
            headers=headers,
            json={"article_text": "too short"}
        )
        assert resp.status_code == 422
        data = resp.json()
        assert data["success"] is False
        assert data["error"]["code"] == "VALIDATION_ERROR"

@pytest.mark.asyncio
async def test_gateway_successful_execution_and_trace():
    mock_result = ProviderResult(
        raw_text='{"title": "Deep Learning Evolution", "summary": "An exploration of neural systems.", "key_points": ["transformer scaling", "inference cost"], "sentiment": "positive", "topics": ["AI", "Hardware"]}',
        parsed_json={
            "title": "Deep Learning Evolution",
            "summary": "An exploration of neural systems.",
            "key_points": ["transformer scaling", "inference cost"],
            "sentiment": "positive",
            "topics": ["AI", "Hardware"]
        },
        input_tokens=150,
        output_tokens=90,
        total_tokens=240,
        latency_ms=315.0,
        provider="openai",
        model="gpt-4o-mini"
    )

    with patch.object(provider_registry.get("openai"), "generate", new=AsyncMock(return_value=mock_result)), \
         patch.object(provider_registry.get("gemini"), "generate", new=AsyncMock(return_value=mock_result)):
        transport = ASGITransport(app=app)
        headers = {"X-API-Key": "nexus-dev-master-key-2026"}
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/run/article-intelligence",
                headers=headers,
                json={
                    "article_text": "Recent advancements in deep neural networks have redefined computational efficiency and latency across enterprise scale deployments."
                }
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["success"] is True
            assert data["data"]["title"] == "Deep Learning Evolution"
            assert data["meta"]["request_id"].startswith("REQ-")
            assert data["meta"]["tokens"]["total"] == 240
            assert len(data["meta"]["trace"]) >= 5

@pytest.mark.asyncio
async def test_gateway_automatic_fallback():
    mock_fallback_result = ProviderResult(
        raw_text='{"name": "Jane Doe", "company": "Acme Corp", "designation": "CTO", "phone": "12345", "email": "jane@acme.com", "website": "acme.com"}',
        parsed_json={
            "name": "Jane Doe",
            "company": "Acme Corp",
            "designation": "CTO",
            "phone": "12345",
            "email": "jane@acme.com",
            "website": "acme.com"
        },
        input_tokens=120,
        output_tokens=60,
        total_tokens=180,
        latency_ms=420.0,
        provider="openai",
        model="gpt-4o-mini"
    )

    # Primary (gemini) raises RateLimit/Timeout, Fallback (openai) succeeds
    primary_mock = AsyncMock(side_effect=RuntimeError("Primary provider 429 Rate Limit Exceeded"))
    fallback_mock = AsyncMock(return_value=mock_fallback_result)

    with patch.object(provider_registry.get("gemini"), "generate", new=primary_mock), \
         patch.object(provider_registry.get("openai"), "generate", new=fallback_mock):
        
        transport = ASGITransport(app=app)
        headers = {"X-API-Key": "nexus-dev-master-key-2026"}
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/run/card-scanner",
                headers=headers,
                json={"image": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="}
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["success"] is True
            assert data["meta"]["fallback_used"] is True
            assert data["meta"]["provider"] == "openai"
            assert data["data"]["company"] == "Acme Corp"

@pytest.mark.asyncio
async def test_disabled_connector():
    transport = ASGITransport(app=app)
    headers = {"X-API-Key": "nexus-dev-master-key-2026"}
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Toggle connector off
        toggle_res = await client.patch("/api/v1/connectors/card-scanner/toggle")
        assert toggle_res.status_code == 200
        assert toggle_res.json()["is_active"] is False

        # Attempt to run
        resp = await client.post(
            "/api/v1/run/card-scanner",
            headers=headers,
            json={"image": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="}
        )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "CONNECTOR_DISABLED"

        # Toggle back on for other tests
        await client.patch("/api/v1/connectors/card-scanner/toggle")

@pytest.mark.asyncio
async def test_analytics_and_logs():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/analytics/dashboard")
        assert resp.status_code == 200
        dash = resp.json()
        assert "overview" in dash
        assert dash["overview"]["total_connectors"] >= 2
        assert "by_provider" in dash

        logs_res = await client.get("/api/v1/analytics/logs")
        assert logs_res.status_code == 200
        logs_data = logs_res.json()
        assert "logs" in logs_data
        assert logs_data["total"] >= 1
