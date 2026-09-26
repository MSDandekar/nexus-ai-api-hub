import time
import json
from typing import Optional, Any
from fastapi import APIRouter, Depends, Request, Header, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.database import get_db
from backend.models import Connector, ConnectorSchema
from backend.services.auth import verify_api_key
from backend.services.input_validator import validate_dynamic_inputs
from backend.services.routing_engine import resolve_model_routing
from backend.services.fallback_service import execute_with_fallback
from backend.services.schema_engine import parse_schema_def, validate_and_normalize_schema
from backend.services.repair_service import attempt_response_repair
from backend.services.cost_catalog import calculate_request_cost
from backend.services.logger_service import generate_request_id, log_request_event
from backend.services.providers.registry import provider_registry

router = APIRouter(prefix="/api/v1", tags=["Gateway"])

async def extract_request_data(request: Request) -> tuple[dict[str, Any], dict[str, Any]]:
    """Extracts raw parameters and uploaded files from JSON or Multipart form."""
    raw_payload = {}
    uploaded_files = {}

    content_type = request.headers.get("content-type", "").lower()

    if "application/json" in content_type:
        try:
            body = await request.body()
            if body:
                raw_payload = json.loads(body.decode("utf-8"))
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "INVALID_JSON_BODY", "message": f"Malformed JSON request body: {str(e)}"}
            )
    elif "multipart/form-data" in content_type or "application/x-www-form-urlencoded" in content_type:
        form = await request.form()
        for k, v in form.items():
            if hasattr(v, "filename"):
                uploaded_files[k] = v
            else:
                raw_payload[k] = v
    else:
        # Fallback to query params or empty JSON
        raw_payload = dict(request.query_params)

    return raw_payload, uploaded_files

def assemble_prompt(inputs_dict: dict[str, Any], system_prompt: str) -> str:
    """Combines user input values into a structured AI context prompt."""
    prompt_lines = ["--- Submitted Parameters ---"]
    for k, v in inputs_dict.items():
        if isinstance(v, (dict, list)):
            prompt_lines.append(f"{k}:\n{json.dumps(v, indent=2)}")
        else:
            prompt_lines.append(f"{k}: {v}")
    prompt_lines.append("--- End Parameters ---")
    prompt_lines.append("\nPlease process the input parameters above according to your instructions.")
    return "\n".join(prompt_lines)

@router.post("/run/{slug}")
@router.post("/connectors/{slug}/run")
async def run_connector(
    slug: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    authorization: Optional[str] = Header(None)
):
    start_total_time = time.perf_counter()
    request_id = generate_request_id()
    trace = []

    trace.append({"step": "Request Received", "status": "ok", "detail": f"Method POST on slug '{slug}'"})

    # 1. Authentication
    api_key_candidate = x_api_key or authorization
    is_authenticated = await verify_api_key(api_key_candidate, db)
    if not is_authenticated:
        elapsed_err = round((time.perf_counter() - start_total_time) * 1000, 2)
        trace.append({"step": "Authentication", "status": "failed", "detail": "Invalid or missing API key"})
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "success": False,
                "data": None,
                "error": {
                    "code": "UNAUTHORIZED",
                    "message": "Invalid or missing API Key. Provide a valid 'X-API-Key' header or Bearer token.",
                    "details": []
                },
                "meta": {
                    "request_id": request_id,
                    "response_time_ms": elapsed_err,
                    "trace": trace
                }
            }
        )
    trace.append({"step": "Authentication", "status": "ok", "detail": "Valid API key authorized"})

    # 2. Load Connector
    res = await db.execute(select(Connector).where(Connector.slug == slug))
    connector = res.scalars().first()
    if not connector:
        elapsed_err = round((time.perf_counter() - start_total_time) * 1000, 2)
        trace.append({"step": "Connector Lookup", "status": "failed", "detail": f"Connector '{slug}' not found"})
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "success": False,
                "data": None,
                "error": {
                    "code": "NOT_FOUND",
                    "message": f"Connector with slug '{slug}' does not exist.",
                    "details": []
                },
                "meta": {
                    "request_id": request_id,
                    "response_time_ms": elapsed_err,
                    "trace": trace
                }
            }
        )

    if not connector.is_active:
        elapsed_err = round((time.perf_counter() - start_total_time) * 1000, 2)
        trace.append({"step": "Connector Status", "status": "failed", "detail": "Connector is currently disabled"})
        # Log disabled invocation attempt
        await log_request_event(
            db=db,
            request_id=request_id,
            connector_id=connector.id,
            connector_slug=connector.slug,
            provider=connector.provider,
            model=connector.model_id,
            status="failure",
            response_time_ms=elapsed_err,
            error_code="CONNECTOR_DISABLED",
            error_message="Connector is disabled by administrator."
        )
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={
                "success": False,
                "data": None,
                "error": {
                    "code": "CONNECTOR_DISABLED",
                    "message": f"Connector '{connector.name}' is currently disabled by administrator.",
                    "details": []
                },
                "meta": {
                    "request_id": request_id,
                    "response_time_ms": elapsed_err,
                    "trace": trace
                }
            }
        )
    trace.append({"step": "Connector Loaded", "status": "ok", "detail": f"Loaded '{connector.name}' (active)"})

    # 3. Parse & Validate Dynamic Inputs
    try:
        raw_payload, uploaded_files = await extract_request_data(request)
    except HTTPException as h_err:
        elapsed_err = round((time.perf_counter() - start_total_time) * 1000, 2)
        trace.append({"step": "Payload Extraction", "status": "failed", "detail": str(h_err.detail)})
        return JSONResponse(
            status_code=h_err.status_code,
            content={
                "success": False,
                "data": None,
                "error": h_err.detail,
                "meta": {"request_id": request_id, "response_time_ms": elapsed_err, "trace": trace}
            }
        )

    validation_result = validate_dynamic_inputs(
        input_definitions=connector.inputs,
        raw_payload=raw_payload,
        uploaded_files=uploaded_files
    )

    if not validation_result.is_valid:
        elapsed_err = round((time.perf_counter() - start_total_time) * 1000, 2)
        trace.append({"step": "Input Validation", "status": "failed", "detail": "; ".join(validation_result.errors)})
        await log_request_event(
            db=db,
            request_id=request_id,
            connector_id=connector.id,
            connector_slug=connector.slug,
            provider=connector.provider,
            model=connector.model_id,
            status="failure",
            response_time_ms=elapsed_err,
            error_code="VALIDATION_ERROR",
            error_message="; ".join(validation_result.errors),
            request_payload=raw_payload
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "success": False,
                "data": None,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Input validation failed for dynamic connector parameters.",
                    "details": validation_result.errors
                },
                "meta": {
                    "request_id": request_id,
                    "response_time_ms": elapsed_err,
                    "trace": trace
                }
            }
        )
    trace.append({"step": "Input Validation", "status": "ok", "detail": f"{len(connector.inputs)} input fields verified"})

    # 4. Resolve Output Schema
    schema_def = {}
    if connector.schema_definition and connector.schema_definition.schema_json:
        schema_def = parse_schema_def(connector.schema_definition.schema_json)

    # 5. Intelligent Routing
    has_images = len(validation_result.images) > 0
    has_files = len(validation_result.files) > 0
    prompt_text = assemble_prompt(validation_result.cleaned_data, connector.system_prompt)

    routing_decision = resolve_model_routing(
        strategy=connector.routing_strategy,
        default_provider=connector.provider,
        default_model=connector.model_id,
        has_images=has_images,
        has_files=has_files,
        has_schema=bool(schema_def),
        prompt_len=len(prompt_text)
    )
    trace.append({
        "step": "Model Routing",
        "status": "ok",
        "detail": f"Strategy: {routing_decision.strategy.upper()} -> {routing_decision.selected_provider}/{routing_decision.selected_model} ({routing_decision.reason})"
    })

    # 6. Execute AI Request with Automatic Fallback
    fallback_used = False
    fallback_prov = None
    fallback_mod = None
    repair_attempted = False
    final_result = None

    try:
        report = await execute_with_fallback(
            provider_name=routing_decision.selected_provider,
            model_id=routing_decision.selected_model,
            prompt=prompt_text,
            system_prompt=connector.system_prompt,
            json_schema=schema_def,
            images=validation_result.images,
            files=validation_result.files,
            fallback_enabled=connector.fallback_enabled,
            fallback_provider=connector.fallback_provider,
            fallback_model=connector.fallback_model,
            temperature=0.1
        )
        final_result = report.result
        fallback_used = report.fallback_used
        fallback_prov = report.fallback_provider
        fallback_mod = report.fallback_model
        
        if fallback_used:
            trace.append({
                "step": "AI Inference (Fallback)",
                "status": "warning",
                "detail": f"Primary {report.primary_provider}/{report.primary_model} failed ({report.primary_error}). Succeeded on fallback {fallback_prov}/{fallback_mod} in {final_result.latency_ms}ms"
            })
        else:
            trace.append({
                "step": "AI Inference",
                "status": "ok",
                "detail": f"Completed via {final_result.provider}/{final_result.model} in {final_result.latency_ms}ms"
            })

    except Exception as exec_err:
        elapsed_err = round((time.perf_counter() - start_total_time) * 1000, 2)
        trace.append({"step": "AI Inference", "status": "failed", "detail": str(exec_err)})
        await log_request_event(
            db=db,
            request_id=request_id,
            connector_id=connector.id,
            connector_slug=connector.slug,
            provider=routing_decision.selected_provider,
            model=routing_decision.selected_model,
            status="failure",
            response_time_ms=elapsed_err,
            routing_strategy=routing_decision.strategy,
            routing_reason=routing_decision.reason,
            fallback_used=connector.fallback_enabled,
            fallback_provider=connector.fallback_provider,
            fallback_model=connector.fallback_model,
            error_code="PROVIDER_ERROR",
            error_message=str(exec_err),
            request_payload=validation_result.cleaned_data
        )
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={
                "success": False,
                "data": None,
                "error": {
                    "code": "PROVIDER_ERROR",
                    "message": "AI Provider inference execution failed.",
                    "details": [str(exec_err)]
                },
                "meta": {
                    "request_id": request_id,
                    "response_time_ms": elapsed_err,
                    "trace": trace
                }
            }
        )

    # 7. Output Schema Validation & Automatic Response Repair
    output_data = final_result.parsed_json
    val_schema_res = validate_and_normalize_schema(output_data, schema_def)

    if not val_schema_res.is_valid:
        trace.append({
            "step": "Schema Validation",
            "status": "warning",
            "detail": f"Initial output failed schema validation: {val_schema_res.errors}. Attempting automatic repair..."
        })
        # Attempt repair
        repair_res = await attempt_response_repair(
            raw_text=final_result.raw_text,
            schema_def=schema_def,
            provider=provider_registry.get(final_result.provider) if provider_registry.get(final_result.provider).is_configured() else None,
            model_id=final_result.model
        )
        repair_attempted = True

        if repair_res.success:
            output_data = repair_res.data
            trace.append({
                "step": "Response Repair",
                "status": "ok",
                "detail": f"Successfully repaired output via method '{repair_res.method}'"
            })
        else:
            trace.append({
                "step": "Response Repair",
                "status": "failed",
                "detail": repair_res.error or "Repair could not recover valid schema"
            })
            # Still return parsed json or raw text if possible, with warning
            output_data = final_result.parsed_json or {"raw_output": final_result.raw_text}
    else:
        output_data = val_schema_res.data
        trace.append({"step": "Schema Validation", "status": "ok", "detail": "Output matches configured schema"})

    # 8. Token & Cost Accounting
    total_time_ms = round((time.perf_counter() - start_total_time) * 1000, 2)
    in_tokens = final_result.input_tokens
    out_tokens = final_result.output_tokens
    tot_tokens = final_result.total_tokens or (in_tokens + out_tokens)
    est_cost = calculate_request_cost(final_result.model, in_tokens, out_tokens)

    # 9. Persistent Usage Logging
    final_status = "repaired" if repair_attempted else "success"
    await log_request_event(
        db=db,
        request_id=request_id,
        connector_id=connector.id,
        connector_slug=connector.slug,
        provider=final_result.provider,
        model=final_result.model,
        status=final_status,
        response_time_ms=total_time_ms,
        input_tokens=in_tokens,
        output_tokens=out_tokens,
        total_tokens=tot_tokens,
        estimated_cost=est_cost,
        routing_strategy=routing_decision.strategy,
        routing_reason=routing_decision.reason,
        fallback_used=fallback_used,
        fallback_provider=fallback_prov,
        fallback_model=fallback_mod,
        repair_attempted=repair_attempted,
        request_payload=validation_result.cleaned_data,
        response_payload=output_data
    )
    trace.append({"step": "Persistent Logging", "status": "ok", "detail": f"Logged request {request_id} (Cost: ${est_cost:.6f})"})

    # 10. Return Standard Envelope
    return {
        "success": True,
        "data": output_data,
        "error": None,
        "meta": {
            "request_id": request_id,
            "connector": connector.slug,
            "provider": final_result.provider,
            "model": final_result.model,
            "routing": {
                "strategy": routing_decision.strategy,
                "task_type": routing_decision.task_type,
                "reason": routing_decision.reason,
                "candidates_evaluated": routing_decision.candidate_count
            },
            "fallback_used": fallback_used,
            "fallback_info": {
                "provider": fallback_prov,
                "model": fallback_mod
            } if fallback_used else None,
            "repair_attempted": repair_attempted,
            "response_time_ms": total_time_ms,
            "tokens": {
                "input": in_tokens,
                "output": out_tokens,
                "total": tot_tokens
            },
            "estimated_cost_usd": est_cost,
            "trace": trace
        }
    }
