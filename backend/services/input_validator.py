import json
import base64
from typing import Any, Optional
from pydantic import BaseModel
from backend.services.providers.base import ImagePayload, FilePayload
from backend.core.config import settings

class ValidationResult(BaseModel):
    is_valid: bool
    cleaned_data: dict[str, Any] = {}
    images: list[ImagePayload] = []
    files: list[FilePayload] = []
    errors: list[str] = []

def parse_rules(rules_raw: Optional[str]) -> dict:
    if not rules_raw:
        return {}
    if isinstance(rules_raw, dict):
        return rules_raw
    try:
        return json.loads(rules_raw)
    except Exception:
        return {}

def validate_dynamic_inputs(
    input_definitions: list[Any],
    raw_payload: dict[str, Any],
    uploaded_files: Optional[dict[str, Any]] = None
) -> ValidationResult:
    cleaned = {}
    images = []
    files = []
    errors = []
    uploaded_files = uploaded_files or {}

    for field in input_definitions:
        name = field.name if hasattr(field, "name") else field.get("name")
        field_type = (field.type if hasattr(field, "type") else field.get("type", "text")).lower()
        is_required = field.is_required if hasattr(field, "is_required") else field.get("is_required", True)
        default_val = field.default_value if hasattr(field, "default_value") else field.get("default_value")
        rules = parse_rules(field.validation_rules if hasattr(field, "validation_rules") else field.get("validation_rules"))

        val = raw_payload.get(name)

        # Check in uploaded files if not in payload
        file_obj = uploaded_files.get(name)

        # If missing, apply default if available
        if val is None and file_obj is None:
            if default_val is not None and default_val != "":
                val = default_val
            elif is_required:
                errors.append(f"Missing required input parameter: '{name}' (type: {field_type})")
                continue
            else:
                cleaned[name] = None
                continue

        # Type validation & conversion
        try:
            if field_type == "text":
                str_val = str(val) if val is not None else ""
                min_len = rules.get("min_length")
                max_len = rules.get("max_length")
                if min_len is not None and len(str_val) < int(min_len):
                    errors.append(f"Field '{name}' length ({len(str_val)}) must be at least {min_len} characters.")
                if max_len is not None and len(str_val) > int(max_len):
                    errors.append(f"Field '{name}' length ({len(str_val)}) exceeds maximum {max_len} characters.")
                cleaned[name] = str_val

            elif field_type == "number":
                num_val = float(val) if "." in str(val) else int(val)
                min_val = rules.get("min")
                max_val = rules.get("max")
                if min_val is not None and num_val < float(min_val):
                    errors.append(f"Field '{name}' value {num_val} is less than minimum {min_val}.")
                if max_val is not None and num_val > float(max_val):
                    errors.append(f"Field '{name}' value {num_val} exceeds maximum {max_val}.")
                cleaned[name] = num_val

            elif field_type == "boolean":
                if isinstance(val, bool):
                    cleaned[name] = val
                elif isinstance(val, (int, float)):
                    cleaned[name] = bool(val)
                elif isinstance(val, str):
                    cleaned[name] = val.strip().lower() in ("true", "1", "yes", "on")
                else:
                    errors.append(f"Field '{name}' must be a valid boolean.")

            elif field_type == "json":
                if isinstance(val, (dict, list)):
                    cleaned[name] = val
                elif isinstance(val, str):
                    try:
                        cleaned[name] = json.loads(val)
                    except json.JSONDecodeError as jde:
                        errors.append(f"Field '{name}' contains invalid JSON: {jde.msg}")
                else:
                    errors.append(f"Field '{name}' must be a JSON object or array.")

            elif field_type == "image":
                # Check file upload or base64 data url / base64 string
                b64_data = None
                mime_type = "image/jpeg"

                if file_obj:
                    # Starlette UploadFile or raw bytes
                    if hasattr(file_obj, "read"):
                        # If async read needed, it will be handled before or synchronously
                        content = file_obj.file.read() if hasattr(file_obj, "file") else file_obj
                    else:
                        content = file_obj
                    if len(content) > settings.MAX_FILE_SIZE_BYTES:
                        errors.append(f"Image '{name}' exceeds maximum size limit of 10MB.")
                        continue
                    b64_data = base64.b64encode(content).decode("utf-8")
                    if hasattr(file_obj, "content_type") and file_obj.content_type:
                        mime_type = file_obj.content_type
                elif isinstance(val, str) and val.strip():
                    raw_str = val.strip()
                    if raw_str.startswith("data:") and ";base64," in raw_str:
                        header, b64_data = raw_str.split(";base64,", 1)
                        mime_type = header.replace("data:", "")
                    else:
                        b64_data = raw_str

                if not b64_data:
                    if is_required:
                        errors.append(f"Field '{name}' requires an image upload or valid base64 image data.")
                else:
                    img_payload = ImagePayload(mime_type=mime_type, base64_data=b64_data)
                    images.append(img_payload)
                    cleaned[name] = f"[Image: {mime_type}, {len(b64_data)} bytes base64]"

            elif field_type == "file":
                b64_data = None
                mime_type = "application/octet-stream"
                file_name = f"{name}.bin"
                text_content = None

                if file_obj:
                    content = file_obj.file.read() if hasattr(file_obj, "file") else file_obj
                    if len(content) > settings.MAX_FILE_SIZE_BYTES:
                        errors.append(f"File '{name}' exceeds maximum size limit of 10MB.")
                        continue
                    b64_data = base64.b64encode(content).decode("utf-8")
                    file_name = getattr(file_obj, "filename", file_name)
                    mime_type = getattr(file_obj, "content_type", mime_type)
                    try:
                        text_content = content.decode("utf-8")
                    except Exception:
                        text_content = None
                elif isinstance(val, str):
                    text_content = val
                    b64_data = base64.b64encode(val.encode("utf-8")).decode("utf-8")
                    mime_type = "text/plain"

                if not b64_data and not text_content:
                    if is_required:
                        errors.append(f"Field '{name}' requires a file upload or text content.")
                else:
                    f_payload = FilePayload(
                        mime_type=mime_type,
                        file_name=file_name,
                        base64_data=b64_data or "",
                        text_content=text_content
                    )
                    files.append(f_payload)
                    cleaned[name] = f"[File: {file_name}, {mime_type}]"

        except Exception as e:
            errors.append(f"Failed to process field '{name}': {str(e)}")

    return ValidationResult(
        is_valid=(len(errors) == 0),
        cleaned_data=cleaned,
        images=images,
        files=files,
        errors=errors
    )
