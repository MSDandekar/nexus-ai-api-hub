import json
import re
from typing import Optional, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func
from backend.database import get_db
from backend.models import Connector, ConnectorInput, ConnectorSchema, RequestLog, utcnow
from backend.services.cost_catalog import DEFAULT_MODEL_CATALOG
from backend.services.providers.registry import provider_registry

router = APIRouter(prefix="/api/v1/connectors", tags=["Connectors"])

class ConnectorInputDTO(BaseModel):
    name: str
    type: str  # text, number, boolean, image, file, json
    is_required: bool = True
    description: Optional[str] = None
    default_value: Optional[str] = None
    validation_rules: Optional[Any] = None

class ConnectorCreateDTO(BaseModel):
    name: str
    slug: Optional[str] = None
    description: Optional[str] = None
    provider: str = "gemini"
    model_id: str = "gemini-2.5-flash"
    system_prompt: str
    routing_strategy: str = "specific"  # specific, cheapest, fastest, balanced, highest_quality, auto
    fallback_enabled: bool = True
    fallback_provider: Optional[str] = None
    fallback_model: Optional[str] = None
    is_active: bool = True
    inputs: list[ConnectorInputDTO] = []
    schema_definition: Optional[Any] = None  # JSON string or dict

class ConnectorUpdateDTO(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    provider: Optional[str] = None
    model_id: Optional[str] = None
    system_prompt: Optional[str] = None
    routing_strategy: Optional[str] = None
    fallback_enabled: Optional[bool] = None
    fallback_provider: Optional[str] = None
    fallback_model: Optional[str] = None
    is_active: Optional[bool] = None
    inputs: Optional[list[ConnectorInputDTO]] = None
    schema_definition: Optional[Any] = None

def slugify(text: str) -> str:
    cleaned = re.sub(r'[^a-zA-Z0-9\s-]', '', text).strip().lower()
    return re.sub(r'[\s-]+', '-', cleaned)

@router.get("")
async def list_connectors(db: AsyncSession = Depends(get_db)):
    query = select(Connector).order_by(Connector.created_at.desc())
    res = await db.execute(query)
    connectors = res.scalars().all()

    # Get request counts per connector
    counts_query = select(RequestLog.connector_slug, func.count(RequestLog.id)).group_by(RequestLog.connector_slug)
    counts_res = await db.execute(counts_query)
    req_counts = dict(counts_res.all())

    items = []
    for c in connectors:
        schema_dict = {}
        if c.schema_definition and c.schema_definition.schema_json:
            try:
                schema_dict = json.loads(c.schema_definition.schema_json)
            except Exception:
                schema_dict = {}

        items.append({
            "id": c.id,
            "slug": c.slug,
            "name": c.name,
            "description": c.description,
            "provider": c.provider,
            "model_id": c.model_id,
            "routing_strategy": c.routing_strategy,
            "fallback_enabled": c.fallback_enabled,
            "fallback_provider": c.fallback_provider,
            "fallback_model": c.fallback_model,
            "is_active": c.is_active,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "updated_at": c.updated_at.isoformat() if c.updated_at else None,
            "request_count": req_counts.get(c.slug, 0),
            "inputs": [
                {
                    "name": inp.name,
                    "type": inp.type,
                    "is_required": inp.is_required,
                    "description": inp.description,
                    "default_value": inp.default_value
                }
                for inp in c.inputs
            ],
            "schema_definition": schema_dict
        })

    return {"connectors": items, "total": len(items)}

@router.get("/{slug}")
async def get_connector(slug: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Connector).where(Connector.slug == slug))
    c = res.scalars().first()
    if not c:
        raise HTTPException(status_code=404, detail="Connector not found")

    schema_dict = {}
    if c.schema_definition and c.schema_definition.schema_json:
        try:
            schema_dict = json.loads(c.schema_definition.schema_json)
        except Exception:
            schema_dict = {}

    return {
        "id": c.id,
        "slug": c.slug,
        "name": c.name,
        "description": c.description,
        "provider": c.provider,
        "model_id": c.model_id,
        "system_prompt": c.system_prompt,
        "routing_strategy": c.routing_strategy,
        "fallback_enabled": c.fallback_enabled,
        "fallback_provider": c.fallback_provider,
        "fallback_model": c.fallback_model,
        "is_active": c.is_active,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        "inputs": [
            {
                "name": inp.name,
                "type": inp.type,
                "is_required": inp.is_required,
                "description": inp.description,
                "default_value": inp.default_value,
                "validation_rules": inp.validation_rules
            }
            for inp in c.inputs
        ],
        "schema_definition": schema_dict
    }

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_connector(dto: ConnectorCreateDTO, db: AsyncSession = Depends(get_db)):
    base_slug = dto.slug or slugify(dto.name)
    slug = base_slug

    # Check slug collision
    existing = await db.execute(select(Connector).where(Connector.slug == slug))
    if existing.scalars().first():
        slug = f"{base_slug}-{int(utcnow().timestamp())}"

    connector = Connector(
        slug=slug,
        name=dto.name,
        description=dto.description,
        provider=dto.provider,
        model_id=dto.model_id,
        system_prompt=dto.system_prompt,
        routing_strategy=dto.routing_strategy,
        fallback_enabled=dto.fallback_enabled,
        fallback_provider=dto.fallback_provider,
        fallback_model=dto.fallback_model,
        is_active=dto.is_active,
        created_at=utcnow(),
        updated_at=utcnow()
    )
    db.add(connector)
    await db.flush()

    # Add dynamic inputs
    for inp in dto.inputs:
        rules_str = json.dumps(inp.validation_rules) if isinstance(inp.validation_rules, dict) else (inp.validation_rules or None)
        c_inp = ConnectorInput(
            connector_id=connector.id,
            name=inp.name,
            type=inp.type,
            is_required=inp.is_required,
            description=inp.description,
            default_value=inp.default_value,
            validation_rules=rules_str
        )
        db.add(c_inp)

    # Add schema
    if dto.schema_definition:
        schema_json_str = json.dumps(dto.schema_definition) if isinstance(dto.schema_definition, dict) else str(dto.schema_definition)
        c_schema = ConnectorSchema(
            connector_id=connector.id,
            schema_json=schema_json_str,
            description=f"Output schema for {connector.name}"
        )
        db.add(c_schema)

    await db.commit()
    await db.refresh(connector)
    return {"message": "Connector created successfully", "slug": connector.slug, "id": connector.id}

@router.put("/{slug}")
async def update_connector(slug: str, dto: ConnectorUpdateDTO, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Connector).where(Connector.slug == slug))
    c = res.scalars().first()
    if not c:
        raise HTTPException(status_code=404, detail="Connector not found")

    if dto.name is not None:
        c.name = dto.name
    if dto.description is not None:
        c.description = dto.description
    if dto.provider is not None:
        c.provider = dto.provider
    if dto.model_id is not None:
        c.model_id = dto.model_id
    if dto.system_prompt is not None:
        c.system_prompt = dto.system_prompt
    if dto.routing_strategy is not None:
        c.routing_strategy = dto.routing_strategy
    if dto.fallback_enabled is not None:
        c.fallback_enabled = dto.fallback_enabled
    if dto.fallback_provider is not None:
        c.fallback_provider = dto.fallback_provider
    if dto.fallback_model is not None:
        c.fallback_model = dto.fallback_model
    if dto.is_active is not None:
        c.is_active = dto.is_active
    c.updated_at = utcnow()

    # If inputs provided, replace
    if dto.inputs is not None:
        await db.execute(delete(ConnectorInput).where(ConnectorInput.connector_id == c.id))
        for inp in dto.inputs:
            rules_str = json.dumps(inp.validation_rules) if isinstance(inp.validation_rules, dict) else (inp.validation_rules or None)
            c_inp = ConnectorInput(
                connector_id=c.id,
                name=inp.name,
                type=inp.type,
                is_required=inp.is_required,
                description=inp.description,
                default_value=inp.default_value,
                validation_rules=rules_str
            )
            db.add(c_inp)

    # If schema provided, replace
    if dto.schema_definition is not None:
        await db.execute(delete(ConnectorSchema).where(ConnectorSchema.connector_id == c.id))
        schema_json_str = json.dumps(dto.schema_definition) if isinstance(dto.schema_definition, dict) else str(dto.schema_definition)
        c_schema = ConnectorSchema(
            connector_id=c.id,
            schema_json=schema_json_str,
            description=f"Output schema for {c.name}"
        )
        db.add(c_schema)

    await db.commit()
    return {"message": "Connector updated successfully", "slug": c.slug}

@router.patch("/{slug}/toggle")
async def toggle_connector(slug: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Connector).where(Connector.slug == slug))
    c = res.scalars().first()
    if not c:
        raise HTTPException(status_code=404, detail="Connector not found")

    c.is_active = not c.is_active
    c.updated_at = utcnow()
    await db.commit()
    return {"slug": c.slug, "is_active": c.is_active}

@router.delete("/{slug}")
async def delete_connector(slug: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Connector).where(Connector.slug == slug))
    c = res.scalars().first()
    if not c:
        raise HTTPException(status_code=404, detail="Connector not found")

    await db.delete(c)
    await db.commit()
    return {"message": f"Connector '{slug}' deleted successfully"}

@router.get("/{slug}/docs")
async def get_connector_docs(slug: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Connector).where(Connector.slug == slug))
    c = res.scalars().first()
    if not c:
        raise HTTPException(status_code=404, detail="Connector not found")

    schema_dict = {}
    if c.schema_definition and c.schema_definition.schema_json:
        try:
            schema_dict = json.loads(c.schema_definition.schema_json)
        except Exception:
            schema_dict = {}

    has_files = any(inp.type in ("image", "file") for inp in c.inputs)
    endpoint_path = f"/api/v1/run/{c.slug}"

    # Build sample payload
    sample_json = {}
    curl_body = ""
    if has_files:
        curl_flags = []
        for inp in c.inputs:
            if inp.type in ("image", "file"):
                curl_flags.append(f'-F "{inp.name}=@{inp.name}.jpg"')
            else:
                curl_flags.append(f'-F "{inp.name}=sample_{inp.name}"')
        curl_sample = f"curl -X POST 'https://your-domain.com{endpoint_path}' \\\n  -H 'X-API-Key: YOUR_API_KEY' \\\n  " + " \\\n  ".join(curl_flags)
    else:
        for inp in c.inputs:
            if inp.type == "number":
                sample_json[inp.name] = 100
            elif inp.type == "boolean":
                sample_json[inp.name] = True
            elif inp.type == "json":
                sample_json[inp.name] = {"key": "sample"}
            else:
                sample_json[inp.name] = f"sample {inp.name} value"

        json_str = json.dumps(sample_json, indent=2)
        curl_sample = f"curl -X POST 'https://your-domain.com{endpoint_path}' \\\n  -H 'X-API-Key: YOUR_API_KEY' \\\n  -H 'Content-Type: application/json' \\\n  -d '{json_str}'"

    expected_response = {
        "success": True,
        "data": {k: f"example_{v}" if isinstance(v, str) else v for k, v in schema_dict.items()} if schema_dict else {"result": "example output"},
        "error": None,
        "meta": {
            "request_id": "REQ-20260927-ABC12",
            "connector": c.slug,
            "provider": c.provider,
            "model": c.model_id,
            "routing": {"strategy": c.routing_strategy, "reason": "Evaluated policy"},
            "response_time_ms": 320.5,
            "tokens": {"input": 140, "output": 95, "total": 235},
            "estimated_cost_usd": 0.000085
        }
    }

    return {
        "connector_name": c.name,
        "slug": c.slug,
        "description": c.description,
        "endpoint": endpoint_path,
        "method": "POST",
        "content_type": "multipart/form-data" if has_files else "application/json",
        "authentication": {
            "header": "X-API-Key",
            "alternative": "Authorization: Bearer <key>",
            "required": True
        },
        "provider_info": {
            "configured_provider": c.provider,
            "configured_model": c.model_id,
            "routing_strategy": c.routing_strategy,
            "fallback_enabled": c.fallback_enabled,
            "fallback_provider": c.fallback_provider,
            "fallback_model": c.fallback_model
        },
        "parameters": [
            {
                "name": inp.name,
                "type": inp.type,
                "required": inp.is_required,
                "description": inp.description or "",
                "default": inp.default_value
            }
            for inp in c.inputs
        ],
        "output_schema": schema_dict,
        "sample_request": sample_json,
        "curl_example": curl_sample,
        "expected_response": expected_response
    }
