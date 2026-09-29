import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport
from backend.main import app
from backend.services.providers.base import (
    ProviderResult, ProviderException, ProviderErrorKind
)
from backend.services.providers.registry import provider_registry

@pytest.mark.asyncio
async def test_1_gemini_succeeds_no_fallback():
    """Test 1: When Gemini succeeds, it is used without fallback."""
    mock_result = ProviderResult(
        raw_text='{"title": "AI Trends", "summary": "Overview", "key_points": ["P1"], "sentiment": "Positive", "topics": ["Tech"]}',
        parsed_json={
            "title": "AI Trends",
            "summary": "Overview",
            "key_points": ["P1"],
            "sentiment": "Positive",
            "topics": ["Tech"]
        },
        input_tokens=100,
        output_tokens=50,
        total_tokens=150,
        latency_ms=310.0,
        provider="gemini",
        model="gemini-3.8-flash"
    )

    with patch.object(provider_registry.get("gemini"), "generate", new=AsyncMock(return_value=mock_result)):
        transport = ASGITransport(app=app)
        headers = {"X-API-Key": "nexus-dev-master-key-2026"}
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/run/article-intelligence",
                headers=headers,
                json={"article_text": "This is a detailed analysis of autonomous multi-agent gateway design patterns."}
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["success"] is True
            assert data["meta"]["fallback_used"] is False
            assert data["meta"]["provider"] == "gemini"
            assert data["meta"]["model"] == "gemini-3.8-flash"
            trace = data["meta"]["trace"]
            # No fallback step in trace
            assert not any(t["step"] == "Fallback" for t in trace)
            inference_steps = [t for t in trace if t["step"] == "AI Inference"]
            assert len(inference_steps) == 1
            assert inference_steps[0]["status"] == "ok"

@pytest.mark.asyncio
async def test_2_gemini_429_falls_back_to_openai():
    """Test 2: When Gemini hits 429 quota, fallback routes to configured OpenAI model."""
    gemini_429_err = ProviderException(
        error_kind=ProviderErrorKind.QUOTA_EXCEEDED,
        message="Gemini quota exceeded (HTTP 429): Free tier daily quota limit reached for gemini-3.8-flash.",
        provider="gemini",
        status_code=429
    )
    mock_openai_result = ProviderResult(
        raw_text='{"title": "OpenAI Handled", "summary": "Extracted via OpenAI", "key_points": ["Cross-provider"], "sentiment": "Neutral", "topics": ["Cloud"]}',
        parsed_json={
            "title": "OpenAI Handled",
            "summary": "Extracted via OpenAI",
            "key_points": ["Cross-provider"],
            "sentiment": "Neutral",
            "topics": ["Cloud"]
        },
        input_tokens=110,
        output_tokens=60,
        total_tokens=170,
        latency_ms=450.0,
        provider="openai",
        model="gpt-4o-mini"
    )

    with patch.object(provider_registry.get("gemini"), "generate", new=AsyncMock(side_effect=gemini_429_err)), \
         patch.object(provider_registry.get("openai"), "is_configured", return_value=True), \
         patch.object(provider_registry.get("openai"), "generate", new=AsyncMock(return_value=mock_openai_result)):

        transport = ASGITransport(app=app)
        headers = {"X-API-Key": "nexus-dev-master-key-2026"}
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/run/article-intelligence",
                headers=headers,
                json={"article_text": "This is a detailed analysis of autonomous multi-agent gateway design patterns."}
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["success"] is True
            assert data["meta"]["fallback_used"] is True
            assert data["meta"]["provider"] == "openai"
            assert data["meta"]["model"] == "gpt-4o-mini"
            assert data["data"]["title"] == "OpenAI Handled"

            # Check trace sequence
            trace = data["meta"]["trace"]
            warning_step = next((t for t in trace if t["step"] == "AI Inference" and t["status"] == "warning"), None)
            assert warning_step is not None
            assert "quota exceeded" in warning_step["detail"].lower()

            fallback_step = next((t for t in trace if t["step"] == "Fallback"), None)
            assert fallback_step is not None
            assert "openai/gpt-4o-mini" in fallback_step["detail"]

            success_step = next((t for t in trace if t["step"] == "AI Inference" and t["status"] == "ok"), None)
            assert success_step is not None
            assert "openai/gpt-4o-mini" in success_step["detail"]

@pytest.mark.asyncio
async def test_3_gemini_429_falls_back_to_groq_when_openai_unavailable():
    """Test 3: When Gemini returns 429 and OpenAI is unavailable, fallback routes to Groq."""
    gemini_429_err = ProviderException(
        error_kind=ProviderErrorKind.QUOTA_EXCEEDED,
        message="Gemini quota exceeded (HTTP 429): Free tier daily quota limit reached.",
        provider="gemini",
        status_code=429
    )
    mock_groq_result = ProviderResult(
        raw_text='{"title": "Groq Handled", "summary": "Extracted via Groq Llama", "key_points": ["Fast inference"], "sentiment": "Positive", "topics": ["OpenSource"]}',
        parsed_json={
            "title": "Groq Handled",
            "summary": "Extracted via Groq Llama",
            "key_points": ["Fast inference"],
            "sentiment": "Positive",
            "topics": ["OpenSource"]
        },
        input_tokens=90,
        output_tokens=40,
        total_tokens=130,
        latency_ms=180.0,
        provider="groq",
        model="llama-3.3-70b-versatile"
    )

    with patch.object(provider_registry.get("gemini"), "generate", new=AsyncMock(side_effect=gemini_429_err)), \
         patch.object(provider_registry.get("openai"), "is_configured", return_value=False), \
         patch.object(provider_registry.get("groq"), "is_configured", return_value=True), \
         patch.object(provider_registry.get("groq"), "generate", new=AsyncMock(return_value=mock_groq_result)):

        transport = ASGITransport(app=app)
        headers = {"X-API-Key": "nexus-dev-master-key-2026"}
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/run/article-intelligence",
                headers=headers,
                json={"article_text": "This is a detailed analysis of autonomous multi-agent gateway design patterns."}
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["success"] is True
            assert data["meta"]["fallback_used"] is True
            assert data["meta"]["provider"] == "groq"
            assert data["data"]["title"] == "Groq Handled"

@pytest.mark.asyncio
async def test_4_gemini_429_no_other_provider_configured():
    """Test 4: When Gemini hits 429 and no other provider is configured, clean error is returned without unhandled exceptions."""
    gemini_429_err = ProviderException(
        error_kind=ProviderErrorKind.QUOTA_EXCEEDED,
        message="Gemini quota exceeded (HTTP 429): Free tier daily quota limit reached.",
        provider="gemini",
        status_code=429
    )

    with patch.object(provider_registry.get("gemini"), "generate", new=AsyncMock(side_effect=gemini_429_err)), \
         patch.object(provider_registry.get("openai"), "is_configured", return_value=False), \
         patch.object(provider_registry.get("groq"), "is_configured", return_value=False):

        transport = ASGITransport(app=app)
        headers = {"X-API-Key": "nexus-dev-master-key-2026"}
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/run/article-intelligence",
                headers=headers,
                json={"article_text": "This is a detailed analysis of autonomous multi-agent gateway design patterns."}
            )
            assert resp.status_code == 502
            data = resp.json()
            assert data["success"] is False
            assert data["error"]["code"] == "PROVIDER_QUOTA_EXCEEDED"
            assert "AI provider quota or availability limit reached" in data["error"]["message"]
            assert "No configured fallback provider was available" in data["error"]["message"]

@pytest.mark.asyncio
async def test_5_gemini_auth_failure_does_not_retry_same_credentials():
    """Test 5: When Gemini fails authentication, it routes to another provider instead of retrying bad credentials."""
    gemini_auth_err = ProviderException(
        error_kind=ProviderErrorKind.AUTHENTICATION_ERROR,
        message="Gemini authentication failed. Please verify API key configuration.",
        provider="gemini",
        status_code=401
    )
    mock_openai_result = ProviderResult(
        raw_text='{"title": "Auth Fallback", "summary": "OpenAI Succeeded", "key_points": ["Healthy Provider"], "sentiment": "Neutral", "topics": ["Security"]}',
        parsed_json={
            "title": "Auth Fallback",
            "summary": "OpenAI Succeeded",
            "key_points": ["Healthy Provider"],
            "sentiment": "Neutral",
            "topics": ["Security"]
        },
        input_tokens=100,
        output_tokens=50,
        total_tokens=150,
        latency_ms=390.0,
        provider="openai",
        model="gpt-4o-mini"
    )

    gemini_mock = AsyncMock(side_effect=gemini_auth_err)
    with patch.object(provider_registry.get("gemini"), "generate", new=gemini_mock), \
         patch.object(provider_registry.get("openai"), "is_configured", return_value=True), \
         patch.object(provider_registry.get("openai"), "generate", new=AsyncMock(return_value=mock_openai_result)):

        transport = ASGITransport(app=app)
        headers = {"X-API-Key": "nexus-dev-master-key-2026"}
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/run/article-intelligence",
                headers=headers,
                json={"article_text": "This is a detailed analysis of autonomous multi-agent gateway design patterns."}
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["success"] is True
            assert data["meta"]["fallback_used"] is True
            assert data["meta"]["provider"] == "openai"
            # Crucial: Gemini should have only been called once, not retried for other Gemini models
            assert gemini_mock.call_count == 1

@pytest.mark.asyncio
async def test_6_dynamically_created_connector_fallback():
    """Test 6: Cross-provider fallback works generically on a dynamically created connector."""
    transport = ASGITransport(app=app)
    headers = {"X-API-Key": "nexus-dev-master-key-2026"}
    slug = "dynamic-nlp-test-connector"

    # Create new dynamic connector
    create_payload = {
        "slug": slug,
        "name": "Dynamic NLP Test Connector",
        "description": "Test connector to verify generic cross-provider fallback.",
        "provider": "gemini",
        "model_id": "gemini-3.8-flash",
        "system_prompt": "You are a test helper. Extract category and score in JSON.",
        "routing_strategy": "balanced",
        "fallback_enabled": True,
        "fallback_provider": "openai",
        "fallback_model": "gpt-4o-mini",
        "inputs": [
            {
                "name": "input_query",
                "type": "text",
                "is_required": True,
                "description": "User query string"
            }
        ],
        "schema_json": {
            "category": "string",
            "confidence": "number"
        }
    }

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create or update connector
        res_create = await client.post("/api/v1/connectors", headers=headers, json=create_payload)
        assert res_create.status_code in (200, 201)

        # Mock primary gemini 429, fallback openai success
        gemini_429 = ProviderException(
            error_kind=ProviderErrorKind.QUOTA_EXCEEDED,
            message="Gemini quota exceeded (HTTP 429)",
            provider="gemini",
            status_code=429
        )
        mock_openai_res = ProviderResult(
            raw_text='{"category": "DevOps", "confidence": 0.98}',
            parsed_json={"category": "DevOps", "confidence": 0.98},
            input_tokens=80,
            output_tokens=30,
            total_tokens=110,
            latency_ms=250.0,
            provider="openai",
            model="gpt-4o-mini"
        )

        with patch.object(provider_registry.get("gemini"), "generate", new=AsyncMock(side_effect=gemini_429)), \
             patch.object(provider_registry.get("openai"), "is_configured", return_value=True), \
             patch.object(provider_registry.get("openai"), "generate", new=AsyncMock(return_value=mock_openai_res)):

            res_run = await client.post(
                f"/api/v1/run/{slug}",
                headers=headers,
                json={"input_query": "How to configure zero-downtime blue-green deployments?"}
            )
            assert res_run.status_code == 200
            run_data = res_run.json()
            assert run_data["success"] is True
            assert run_data["meta"]["fallback_used"] is True
            assert run_data["meta"]["provider"] == "openai"
            assert run_data["data"]["category"] == "DevOps"

@pytest.mark.asyncio
async def test_7_openai_provider_basic_execution():
    """Verify OpenAI provider basic text execution adapter."""
    prov = provider_registry.get("openai")
    mock_resp = {
        "choices": [{"message": {"content": "OK"}}],
        "usage": {"prompt_tokens": 5, "completion_tokens": 2, "total_tokens": 7}
    }
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.return_value = AsyncMock(status_code=200, json=lambda: mock_resp, text='{"choices":[{"message":{"content":"OK"}}]}')
        with patch.object(prov, "is_configured", return_value=True):
            res = await prov.generate(model_id="gpt-4o-mini", prompt="Return the word OK.")
            assert res.raw_text == "OK"
            assert res.provider == "openai"
            assert res.model == "gpt-4o-mini"
            assert res.total_tokens == 7

@pytest.mark.asyncio
async def test_8_openai_structured_output():
    """Verify OpenAI provider structured output with json_schema."""
    prov = provider_registry.get("openai")
    schema = {"status": "string", "count": "number"}
    json_text = '{"status": "active", "count": 42}'
    mock_resp = {
        "choices": [{"message": {"content": f"```json\n{json_text}\n```"}}],
        "usage": {"prompt_tokens": 20, "completion_tokens": 10, "total_tokens": 30}
    }
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.return_value = AsyncMock(status_code=200, json=lambda: mock_resp, text=json_text)
        with patch.object(prov, "is_configured", return_value=True):
            res = await prov.generate(model_id="gpt-4o-mini", prompt="Extract info", json_schema=schema)
            assert res.parsed_json == {"status": "active", "count": 42}

@pytest.mark.asyncio
async def test_9_openai_vision_image_processing():
    """Verify OpenAI provider image/vision payload formatting for Business Card Scanner."""
    from backend.services.providers.base import ImagePayload
    prov = provider_registry.get("openai")
    dummy_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    img = ImagePayload(mime_type="image/png", base64_data=dummy_b64)

    captured_payload = {}
    async def mock_post(url, headers=None, json=None):
        nonlocal captured_payload
        captured_payload = json
        mock_resp_data = {
            "choices": [{"message": {"content": '{"name": "Alice", "company": "Tech Corp"}'}}],
            "usage": {"prompt_tokens": 150, "completion_tokens": 30, "total_tokens": 180}
        }
        return AsyncMock(status_code=200, json=lambda: mock_resp_data, text='{"choices":[{"message":{"content":"{\\"name\\": \\"Alice\\", \\"company\\": \\"Tech Corp\\"}"}}]}')

    with patch("httpx.AsyncClient.post", side_effect=mock_post):
        with patch.object(prov, "is_configured", return_value=True):
            res = await prov.generate(
                model_id="gpt-4o-mini",
                prompt="Extract contact info from this business card",
                images=[img],
                json_schema={"name": "string", "company": "string"}
            )
            assert res.parsed_json["name"] == "Alice"
            # Verify image payload structure sent to OpenAI API
            user_msg = next((m for m in captured_payload["messages"] if m["role"] == "user"), None)
            assert user_msg is not None
            assert isinstance(user_msg["content"], list)
            img_entry = next((c for c in user_msg["content"] if c.get("type") == "image_url"), None)
            assert img_entry is not None
            assert img_entry["image_url"]["url"].startswith("data:image/png;base64,")
            assert not img_entry["image_url"]["url"].startswith("data:image/png;base64,data:")

@pytest.mark.asyncio
async def test_10_gemini_429_openai_failure_preserves_actual_error():
    """Verify that when Gemini hits 429 and OpenAI fallback fails (e.g. 429 quota exhaustion), the actual OpenAI failure is preserved."""
    gemini_429 = ProviderException(
        error_kind=ProviderErrorKind.QUOTA_EXCEEDED,
        message="Gemini quota exceeded (HTTP 429): Free tier daily quota limit reached.",
        provider="gemini",
        status_code=429
    )
    openai_credit_exhausted = ProviderException(
        error_kind=ProviderErrorKind.QUOTA_EXCEEDED,
        message="You have no credits remaining. Add credits to continue using the API.",
        provider="openai",
        status_code=429,
        raw_error='{"error": {"code": "credit_balance_exhausted", "message": "You have no credits remaining."}}'
    )

    with patch.object(provider_registry.get("gemini"), "generate", new=AsyncMock(side_effect=gemini_429)), \
         patch.object(provider_registry.get("openai"), "is_configured", return_value=True), \
         patch.object(provider_registry.get("openai"), "generate", new=AsyncMock(side_effect=openai_credit_exhausted)):

        transport = ASGITransport(app=app)
        headers = {"X-API-Key": "nexus-dev-master-key-2026"}
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/run/card-scanner",
                headers=headers,
                json={"image": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="}
            )
            assert resp.status_code == 502
            data = resp.json()
            assert data["success"] is False
            # Verify actual OpenAI failure is preserved, NOT "No configured fallback provider was available"
            assert "No configured fallback provider was available" not in data["error"]["message"]
            assert "OpenAI quota exceeded" in data["error"]["message"]
            # Verify trace records the OpenAI fallback failure step
            trace = data["meta"]["trace"]
            fb_failed_step = next((t for t in trace if t["step"] == "Fallback Inference" and t["status"] == "failed"), None)
            assert fb_failed_step is not None
            assert "OpenAI" in fb_failed_step["detail"]

