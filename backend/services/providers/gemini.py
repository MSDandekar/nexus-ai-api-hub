import json
import time
import httpx
from typing import Optional, Any
from backend.services.providers.base import AIProvider, ProviderResult, ImagePayload, FilePayload
from backend.core.config import settings

class GeminiProvider(AIProvider):
    @property
    def name(self) -> str:
        return "gemini"

    def is_configured(self) -> bool:
        return bool(settings.GEMINI_API_KEY)

    def supports_vision(self, model_id: str) -> bool:
        # All modern Gemini 1.5 and 2.x/2.5 models support vision
        model_lower = model_id.lower()
        return "gemini" in model_lower

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
            raise ValueError("GEMINI_API_KEY is not configured in environment variables.")

        # Clean model name (remove 'models/' prefix if present)
        clean_model = model_id.replace("models/", "")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{clean_model}:generateContent"

        # Build parts
        parts = []
        if images:
            for img in images:
                parts.append({
                    "inline_data": {
                        "mime_type": img.mime_type,
                        "data": img.base64_data
                    }
                })
        if files:
            for f in files:
                if f.text_content:
                    parts.append({"text": f"--- Attached File: {f.file_name} ---\n{f.text_content}\n--- End File ---"})
                else:
                    parts.append({
                        "inline_data": {
                            "mime_type": f.mime_type,
                            "data": f.base64_data
                        }
                    })

        # Append main prompt text
        full_text_prompt = prompt
        if json_schema:
            schema_str = json.dumps(json_schema, indent=2)
            full_text_prompt += f"\n\nCRITICAL: Respond ONLY with valid, raw JSON conforming strictly to this schema without any markdown wrap or explanations:\n{schema_str}"

        parts.append({"text": full_text_prompt})

        payload: dict[str, Any] = {
            "contents": [
                {
                    "role": "user",
                    "parts": parts
                }
            ],
            "generationConfig": {
                "temperature": temperature,
            }
        }

        if json_schema:
            payload["generationConfig"]["responseMimeType"] = "application/json"

        if system_prompt:
            payload["systemInstruction"] = {
                "parts": [{"text": system_prompt}]
            }

        start_time = time.perf_counter()
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                url,
                params={"key": settings.GEMINI_API_KEY},
                json=payload,
                headers={"Content-Type": "application/json"}
            )
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        if response.status_code != 200:
            error_text = response.text
            raise RuntimeError(f"Gemini API error (HTTP {response.status_code}): {error_text}")

        data = response.json()
        
        # Extract text response
        try:
            candidates = data.get("candidates", [])
            if not candidates:
                raise RuntimeError("Gemini returned empty candidate list.")
            text_result = candidates[0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as e:
            raise RuntimeError(f"Malformed Gemini API response: {e}")

        # Extract tokens
        usage = data.get("usageMetadata", {})
        prompt_tokens = usage.get("promptTokenCount", 0)
        candidates_tokens = usage.get("candidatesTokenCount", 0)
        total_tokens = usage.get("totalTokenCount", prompt_tokens + candidates_tokens)

        # Parse JSON if requested
        parsed = None
        if json_schema or "application/json" in payload.get("generationConfig", {}).get("responseMimeType", ""):
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
            output_tokens=candidates_tokens,
            total_tokens=total_tokens,
            latency_ms=round(elapsed_ms, 2),
            provider="gemini",
            model=clean_model
        )
