import json
import time
import httpx
from typing import Optional, Any
from backend.services.providers.base import (
    AIProvider, ProviderResult, ImagePayload, FilePayload,
    ProviderException, ProviderErrorKind, classify_provider_error
)
from backend.core.config import settings, get_openai_api_key
from backend.services.repair_service import extract_json_block, heuristic_json_fix

class OpenAIProvider(AIProvider):
    @property
    def name(self) -> str:
        return "openai"

    def is_configured(self) -> bool:
        return bool(get_openai_api_key())

    def supports_vision(self, model_id: str) -> bool:
        model_lower = model_id.lower()
        return any(v in model_lower for v in ["gpt-4o", "vision", "gpt-4-turbo"])

    def supports_json(self, model_id: str) -> bool:
        return True

    async def generate(
        self,
        model_id: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        json_schema: Optional[dict] = None,
        images: Optional[list[ImagePayload]] = None,
        files: Optional[list[FilePayload]] = None,
        temperature: float = 0.1
    ) -> ProviderResult:
        api_key = get_openai_api_key()
        if not api_key:
            raise ProviderException(
                error_kind=ProviderErrorKind.AUTHENTICATION_ERROR,
                message="OPENAI_API_KEY is not configured in environment variables.",
                provider="openai"
            )

        url = "https://api.openai.com/v1/chat/completions"
        messages = []

        # System instructions
        effective_system = system_prompt or ""
        if json_schema:
            schema_str = json.dumps(json_schema, indent=2)
            schema_instruction = f"\n\nYou are a structured output extractor. Respond ONLY with valid JSON conforming to this schema:\n{schema_str}"
            effective_system = (effective_system + schema_instruction).strip()

        if effective_system:
            messages.append({"role": "system", "content": effective_system})

        # User message content
        user_content: Any = []
        if images:
            for img in images:
                clean_b64 = img.base64_data.strip()
                if clean_b64.startswith("data:"):
                    img_url = clean_b64
                else:
                    img_url = f"data:{img.mime_type};base64,{clean_b64}"
                user_content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": img_url,
                        "detail": "auto"
                    }
                })
        if files:
            for f in files:
                if f.text_content:
                    user_content.append({
                        "type": "text",
                        "text": f"--- Attached File: {f.file_name} ---\n{f.text_content}\n--- End File ---"
                    })

        user_content.append({"type": "text", "text": prompt})

        # If pure text, can pass simple string
        if not images and not (files and not any(f.text_content for f in files)):
            user_content = prompt
            if files:
                user_text_parts = []
                for f in files:
                    if f.text_content:
                        user_text_parts.append(f"--- File: {f.file_name} ---\n{f.text_content}")
                user_text_parts.append(prompt)
                user_content = "\n\n".join(user_text_parts)

        messages.append({"role": "user", "content": user_content})

        payload: dict[str, Any] = {
            "model": model_id,
            "messages": messages,
            "temperature": temperature,
        }

        if json_schema:
            payload["response_format"] = {"type": "json_object"}

        start_time = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    url,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json=payload
                )
        except httpx.TimeoutException:
            raise ProviderException(
                error_kind=ProviderErrorKind.TIMEOUT,
                message=f"OpenAI request timed out after 60s for {model_id}.",
                provider="openai"
            )
        except Exception as net_err:
            raise ProviderException(
                error_kind=ProviderErrorKind.PROVIDER_ERROR,
                message=f"OpenAI network connection error: {net_err}",
                provider="openai",
                raw_error=str(net_err)
            )

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        if response.status_code != 200:
            kind, msg = classify_provider_error("openai", response.status_code, response.text)
            raise ProviderException(
                error_kind=kind,
                message=msg,
                provider="openai",
                status_code=response.status_code,
                raw_error=response.text
            )

        data = response.json()
        try:
            choice = data["choices"][0]
            text_result = choice["message"]["content"]
        except (KeyError, IndexError) as e:
            raise RuntimeError(f"Malformed OpenAI API response: {e}")

        usage = data.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)

        # Parse JSON if requested
        parsed = None
        if json_schema:
            try:
                parsed = json.loads(text_result)
            except Exception:
                block = extract_json_block(text_result)
                if block:
                    parsed = heuristic_json_fix(block)

        return ProviderResult(
            raw_text=text_result,
            parsed_json=parsed,
            input_tokens=prompt_tokens,
            output_tokens=completion_tokens,
            total_tokens=total_tokens,
            latency_ms=round(elapsed_ms, 2),
            provider="openai",
            model=model_id
        )
