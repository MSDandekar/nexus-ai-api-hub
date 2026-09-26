import json
import time
import httpx
from typing import Optional, Any
from backend.services.providers.base import AIProvider, ProviderResult, ImagePayload, FilePayload
from backend.core.config import settings

class OpenAIProvider(AIProvider):
    @property
    def name(self) -> str:
        return "openai"

    def is_configured(self) -> bool:
        return bool(settings.OPENAI_API_KEY)

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
        if not self.is_configured():
            raise ValueError("OPENAI_API_KEY is not configured in environment variables.")

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
                user_content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{img.mime_type};base64,{img.base64_data}",
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
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                    "Content-Type": "application/json"
                },
                json=payload
            )
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        if response.status_code != 200:
            raise RuntimeError(f"OpenAI API error (HTTP {response.status_code}): {response.text}")

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
            cleaned = text_result.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
            try:
                parsed = json.loads(cleaned)
            except Exception:
                parsed = None

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
