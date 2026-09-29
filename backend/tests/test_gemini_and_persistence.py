import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from backend.main import app
from backend.core.config import get_gemini_api_key, settings
from backend.services.providers.registry import provider_registry

@pytest.mark.asyncio
async def test_gemini_api_key_detected():
    """Verify that GEMINI_API_KEY is detected in backend runtime without leaking secret."""
    key = get_gemini_api_key()
    assert bool(key) is True, "GEMINI_API_KEY must be detected in backend runtime"
    assert len(key) > 10, "GEMINI_API_KEY must be a valid key string"
    prov = provider_registry.get("gemini")
    assert prov.is_configured() is True, "GeminiProvider must report configured=True"

@pytest.mark.asyncio
async def test_real_gemini_article_intelligence_request():
    """Verify real request against article-intelligence with Gemini provider."""
    key = get_gemini_api_key()
    if not key:
        pytest.skip("GEMINI_API_KEY not configured in environment")

    transport = ASGITransport(app=app)
    headers = {"X-API-Key": "nexus-dev-master-key-2026"}
    payload = {
        "article_text": "Autonomous multi-agent orchestration gateways unify heterogeneous LLM providers behind predictable schemas, deterministic cost-aware routing, and transient error fallback policies for high-availability enterprise environments."
    }

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/run/article-intelligence",
            headers=headers,
            json=payload,
            timeout=30.0
        )
        if resp.status_code == 502:
            data = resp.json()
            if data.get("error", {}).get("code") == "PROVIDER_QUOTA_EXCEEDED":
                assert "quota exceeded" in data["error"]["message"].lower()
                assert len(data["meta"]["trace"]) > 0
                return
        assert resp.status_code == 200, f"Expected 200 OK, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data["success"] is True
        assert data["error"] is None

        # Verify structured output fields matching schema
        article_data = data["data"]
        assert "title" in article_data
        assert "summary" in article_data
        assert "key_points" in article_data
        assert "sentiment" in article_data
        assert "topics" in article_data

        # Verify metadata trace and tokens
        meta = data["meta"]
        assert meta["request_id"].startswith("REQ-")
        assert meta["response_time_ms"] > 0
        assert meta["tokens"]["total"] > 0
        assert meta["estimated_cost_usd"] >= 0
        assert len(meta["trace"]) >= 6
