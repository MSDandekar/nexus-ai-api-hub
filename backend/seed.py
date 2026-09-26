import asyncio
import json
from sqlalchemy import select
from backend.database import engine, AsyncSessionLocal, Base
from backend.models import (
    Connector, ConnectorInput, ConnectorSchema, ApiKey,
    ModelCatalogEntry, utcnow
)
from backend.services.auth import hash_key
from backend.services.cost_catalog import DEFAULT_MODEL_CATALOG
from backend.core.config import settings

async def seed_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        # 1. Seed Model Catalog
        for model in DEFAULT_MODEL_CATALOG:
            res = await session.execute(
                select(ModelCatalogEntry).where(ModelCatalogEntry.model_id == model.model_id)
            )
            if not res.scalars().first():
                entry = ModelCatalogEntry(
                    provider=model.provider,
                    model_id=model.model_id,
                    display_name=model.display_name,
                    supports_text=model.supports_text,
                    supports_vision=model.supports_vision,
                    supports_json=model.supports_json,
                    input_cost_per_m=model.input_cost_per_m,
                    output_cost_per_m=model.output_cost_per_m,
                    quality_score=model.quality_score,
                    speed_score=model.speed_score,
                    is_enabled=model.is_enabled
                )
                session.add(entry)

        # 2. Seed Default Admin Master API Key
        master_raw = settings.DEFAULT_ADMIN_API_KEY
        master_hash = hash_key(master_raw)
        res_key = await session.execute(
            select(ApiKey).where(ApiKey.hashed_key == master_hash)
        )
        if not res_key.scalars().first():
            admin_key = ApiKey(
                name="Default Master Admin Key",
                key_prefix="nexus-dev-...",
                hashed_key=master_hash,
                is_active=True
            )
            session.add(admin_key)

        # 3. Seed Connector 1: Business Card Scanner (Image / Vision, Gemini with OpenAI fallback)
        res_c1 = await session.execute(
            select(Connector).where(Connector.slug == "card-scanner")
        )
        if not res_c1.scalars().first():
            c1 = Connector(
                slug="card-scanner",
                name="Business Card Scanner",
                description="Extracts structured contact details, company information, and digital profiles from business card photos or document scans.",
                provider="gemini",
                model_id="gemini-2.5-flash",
                system_prompt="You are an expert OCR and contact information extraction agent. Examine the provided business card image carefully. Extract all discernible contact and company fields accurately.",
                routing_strategy="balanced",
                fallback_enabled=True,
                fallback_provider="openai",
                fallback_model="gpt-4o-mini",
                is_active=True
            )
            session.add(c1)
            await session.flush()

            # Dynamic Input: image
            in1 = ConnectorInput(
                connector_id=c1.id,
                name="image",
                type="image",
                is_required=True,
                description="Photo or scanned image of the business card (JPEG, PNG, WebP)",
                default_value=None,
                validation_rules=json.dumps({"max_size_mb": 10})
            )
            session.add(in1)

            # Structured Schema
            schema1 = ConnectorSchema(
                connector_id=c1.id,
                schema_json=json.dumps({
                    "name": "string",
                    "company": "string",
                    "designation": "string",
                    "phone": "string",
                    "email": "string",
                    "website": "string"
                }, indent=2),
                description="Standard contact JSON card structure"
            )
            session.add(schema1)

        # 4. Seed Connector 2: Article Intelligence (Text, OpenAI with Gemini fallback)
        res_c2 = await session.execute(
            select(Connector).where(Connector.slug == "article-intelligence")
        )
        if not res_c2.scalars().first():
            c2 = Connector(
                slug="article-intelligence",
                name="Article Intelligence",
                description="Performs deep comprehension, key takeaway synthesis, sentiment classification, and topic tagging on articles, memos, and essays.",
                provider="openai",
                model_id="gpt-4o-mini",
                system_prompt="You are a professional editorial analyst. Analyze the submitted article or text. Extract the core title, concise executive summary, bulleted key points, overall sentiment, and relevant thematic topics.",
                routing_strategy="balanced",
                fallback_enabled=True,
                fallback_provider="gemini",
                fallback_model="gemini-2.5-flash",
                is_active=True
            )
            session.add(c2)
            await session.flush()

            # Dynamic Inputs: article_text (required), focus_area (optional)
            in2_1 = ConnectorInput(
                connector_id=c2.id,
                name="article_text",
                type="text",
                is_required=True,
                description="The full body text of the article or document to analyze",
                default_value=None,
                validation_rules=json.dumps({"min_length": 20})
            )
            in2_2 = ConnectorInput(
                connector_id=c2.id,
                name="focus_area",
                type="text",
                is_required=False,
                description="Optional domain angle (e.g. Technology, Finance, Healthcare, General)",
                default_value="General",
                validation_rules=None
            )
            session.add_all([in2_1, in2_2])

            # Structured Schema
            schema2 = ConnectorSchema(
                connector_id=c2.id,
                schema_json=json.dumps({
                    "title": "string",
                    "summary": "string",
                    "key_points": "array",
                    "sentiment": "string",
                    "topics": "array"
                }, indent=2),
                description="Comprehensive editorial summary and taxonomy"
            )
            session.add(schema2)

        await session.commit()

if __name__ == "__main__":
    asyncio.run(seed_database())
    print("Database schema and demonstration connectors seeded successfully.")
