import json
import time
import httpx
from typing import Optional, Any
from backend.services.providers.base import (
    AIProvider, ProviderResult, ImagePayload, FilePayload,
    ProviderException, ProviderErrorKind, classify_provider_error
)
from backend.core.config import settings

class GroqProvider(AIProvider):
    @property
    def name(self) -> str:
        return "groq"

    def is_configured(self) -> bool:
        return bool(settings.GROQ_API_KEY)

    def supports_vision(self, model_id: str) -> bool:
        return "vision" in model_id.lower() or "llama-3.2" in model_id.lower()

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
        if not self.is_configured():
            raise ProviderException(
                error_kind=ProviderErrorKind.AUTHENTICATION_ERROR,
                message="GROQ_API_KEY is not configured in environment variables.",
                provider="groq"
            )

        url = "https://api.groq.com/openai/v1/chat/completions"
        messages = []

        effective_system = system_prompt or ""
        if json_schema:
            schema_str = json.dumps(json_schema, indent=2)
            schema_instruction = f"\n\nYou are a structured output extractor. Respond ONLY with valid JSON conforming to this schema:\n{schema_str}"
            effective_system = (effective_system + schema_instruction).strip()

        if effective_system:
            messages.append({"role": "system", "content": effective_system})

        messages.append({"role": "user", "content": prompt})

        payload: dict[str, Any] = {
            "model": model_id,
            "messages": messages,
            "temperature": temperature,
        }

        if json_schema:
            payload["response_format"] = {"type": "json_object"}

        start_time = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                response = await client.post(
                    url,
                    headers={
                        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json=payload
                )
        except httpx.TimeoutException:
            raise ProviderException(
                error_kind=ProviderErrorKind.TIMEOUT,
                message=f"Groq request timed out after 45s for {model_id}.",
                provider="groq"
            )
        except Exception as net_err:
            raise ProviderException(
                error_kind=ProviderErrorKind.PROVIDER_ERROR,
                message=f"Groq network connection error: {net_err}",
                provider="groq",
                raw_error=str(net_err)
            )

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        if response.status_code != 200:
            kind, msg = classify_provider_error("groq", response.status_code, response.text)
            raise ProviderException(
                error_kind=kind,
                message=msg,
                provider="groq",
                status_code=response.status_code,
                raw_error=response.text
            )

        data = response.json()
        try:
            choice = data["choices"][0]
            text_result = choice["message"]["content"]
        except (KeyError, IndexError) as e:
            raise RuntimeError(f"Malformed Groq API response: {e}")

        usage = data.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)

        parsed = None
        if json_schema:
            cleaned = text_result.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            try:
                parsed = json.loads(cleaned.strip())
            except Exception:
                parsed = None

        return ProviderResult(
            raw_text=text_result,
            parsed_json=parsed,
            input_tokens=prompt_tokens,
            output_tokens=completion_tokens,
            total_tokens=total_tokens,
            latency_ms=round(elapsed_ms, 2),
            provider="groq",
            model=model_id
        )
