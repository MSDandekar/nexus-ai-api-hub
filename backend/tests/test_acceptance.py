import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch

from backend.main import app
from backend.seed import seed_database
from backend.services.providers.base import ProviderResult
from backend.services.providers.registry import provider_registry

@pytest_asyncio.fixture(autouse=True)
async def prepare_db():
    await seed_database()

@pytest.mark.asyncio
async def test_acceptance_scenarios_a_through_g():
    transport = ASGITransport(app=app)
    master_key = "nexus-dev-master-key-2026"
    headers = {"X-API-Key": master_key}

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # ----------------------------------------------------
        # SCENARIO A — Create connector & verify endpoint + docs
        # ----------------------------------------------------
        create_payload = {
            "name": "Custom Invoice Extractor",
            "slug": "custom-invoice-extractor",
            "description": "Extracts total and vendor from invoices.",
            "provider": "gemini",
            "model_id": "gemini-2.5-flash",
            "system_prompt": "Extract invoice fields accurately.",
            "routing_strategy": "balanced",
            "fallback_enabled": True,
            "fallback_provider": "openai",
            "fallback_model": "gpt-4o-mini",
            "is_active": True,
            "inputs": [
                {"name": "invoice_image", "type": "image", "is_required": True, "description": "Invoice scan"},
                {"name": "currency", "type": "text", "is_required": False, "default_value": "USD"}
            ],
            "schema_definition": {
                "vendor": "string",
                "total": "number",
                "invoice_number": "string"
            }
        }
        res_create = await client.post("/api/v1/connectors", json=create_payload)
        assert res_create.status_code == 201
        assert res_create.json()["slug"] == "custom-invoice-extractor"

        # Verify docs exist
        res_docs = await client.get("/api/v1/connectors/custom-invoice-extractor/docs")
        assert res_docs.status_code == 200
        docs_data = res_docs.json()
        assert docs_data["endpoint"] == "/api/v1/run/custom-invoice-extractor"
        assert "curl_example" in docs_data
        assert "output_schema" in docs_data

        # ----------------------------------------------------
        # SCENARIO B & C — Test connector & External API call
        # ----------------------------------------------------
        invoice_mock = ProviderResult(
            raw_text='{"vendor": "Apex Logistics", "total": 1420.50, "invoice_number": "INV-9921"}',
            parsed_json={"vendor": "Apex Logistics", "total": 1420.50, "invoice_number": "INV-9921"},
            input_tokens=220,
            output_tokens=45,
            total_tokens=265,
            latency_ms=280.0,
            provider="gemini",
            model="gemini-2.5-flash"
        )

        with patch.object(provider_registry.get("gemini"), "generate", new=AsyncMock(return_value=invoice_mock)), \
             patch.object(provider_registry.get("openai"), "generate", new=AsyncMock(return_value=invoice_mock)):

            res_run = await client.post(
                "/api/v1/run/custom-invoice-extractor",
                headers=headers,
                json={"invoice_image": "data:image/jpeg;base64,/9j/4AAQSkZJRg=="}
            )
            assert res_run.status_code == 200
            run_data = res_run.json()
            assert run_data["success"] is True
            assert run_data["data"]["vendor"] == "Apex Logistics"
            assert run_data["data"]["total"] == 1420.50
            assert "request_id" in run_data["meta"]
            assert run_data["meta"]["tokens"]["total"] == 265
            assert run_data["meta"]["estimated_cost_usd"] > 0
            assert len(run_data["meta"]["trace"]) >= 5

        # ----------------------------------------------------
        # SCENARIO D — Second connector: Article Intelligence
        # ----------------------------------------------------
        article_mock = ProviderResult(
            raw_text='{"title": "Autonomous Systems", "summary": "Study of multi-agent protocols", "key_points": ["coordination", "safety"], "sentiment": "neutral", "topics": ["agents", "AI"]}',
            parsed_json={
                "title": "Autonomous Systems",
                "summary": "Study of multi-agent protocols",
                "key_points": ["coordination", "safety"],
                "sentiment": "neutral",
                "topics": ["agents", "AI"]
            },
            input_tokens=180,
            output_tokens=70,
            total_tokens=250,
            latency_ms=310.0,
            provider="openai",
            model="gpt-4o-mini"
        )
        with patch.object(provider_registry.get("openai"), "generate", new=AsyncMock(return_value=article_mock)), \
             patch.object(provider_registry.get("gemini"), "generate", new=AsyncMock(return_value=article_mock)):

            res_art = await client.post(
                "/api/v1/run/article-intelligence",
                headers=headers,
                json={"article_text": "Evaluating multi-agent coordination paradigms in complex distributed environments."}
            )
            assert res_art.status_code == 200
            assert res_art.json()["data"]["title"] == "Autonomous Systems"

        # ----------------------------------------------------
        # SCENARIO E — Failure Cases (Invalid Key, Missing Input, Disabled)
        # ----------------------------------------------------
        # Invalid API Key
        res_bad_key = await client.post(
            "/api/v1/run/article-intelligence",
            headers={"X-API-Key": "invalid-bogus-key"},
            json={"article_text": "This should be rejected due to auth"}
        )
        assert res_bad_key.status_code == 401
        assert res_bad_key.json()["error"]["code"] == "UNAUTHORIZED"

        # Missing required parameter
        res_missing = await client.post(
            "/api/v1/run/article-intelligence",
            headers=headers,
            json={}
        )
        assert res_missing.status_code == 422
        assert res_missing.json()["error"]["code"] == "VALIDATION_ERROR"

        # ----------------------------------------------------
        # SCENARIO F — Routing (Auto/Balanced Decision & Reason)
        # ----------------------------------------------------
        assert "routing" in run_data["meta"]
        assert run_data["meta"]["routing"]["strategy"] == "balanced"
        assert len(run_data["meta"]["routing"]["reason"]) > 10

        # ----------------------------------------------------
        # SCENARIO G — Fallback (Primary Fails -> Fallback Succeeds)
        # ----------------------------------------------------
        card_fallback_mock = ProviderResult(
            raw_text='{"name": "Alex Mercer", "company": "Gentek", "designation": "Researcher", "phone": "555-0100", "email": "alex@gentek.com", "website": "gentek.com"}',
            parsed_json={"name": "Alex Mercer", "company": "Gentek", "designation": "Researcher", "phone": "555-0100", "email": "alex@gentek.com", "website": "gentek.com"},
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
            latency_ms=450.0,
            provider="openai",
            model="gpt-4o-mini"
        )
        primary_fail_mock = AsyncMock(side_effect=RuntimeError("Google 503 Service Unavailable"))
        fallback_ok_mock = AsyncMock(return_value=card_fallback_mock)

        with patch.object(provider_registry.get("gemini"), "generate", new=primary_fail_mock), \
             patch.object(provider_registry.get("openai"), "generate", new=fallback_ok_mock):

            res_fb = await client.post(
                "/api/v1/run/card-scanner",
                headers=headers,
                json={"image": "data:image/jpeg;base64,/9j/4AAQSkZJRg=="}
            )
            assert res_fb.status_code == 200
            fb_json = res_fb.json()
            assert fb_json["success"] is True
            assert fb_json["meta"]["fallback_used"] is True
            assert fb_json["meta"]["provider"] == "openai"
            assert fb_json["data"]["company"] == "Gentek"
