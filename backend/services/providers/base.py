from abc import ABC, abstractmethod
from typing import Optional, Any
from enum import Enum
from pydantic import BaseModel, Field

class ProviderErrorKind(str, Enum):
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"
    RATE_LIMITED = "RATE_LIMITED"
    MODEL_UNAVAILABLE = "MODEL_UNAVAILABLE"
    PROVIDER_ERROR = "PROVIDER_ERROR"
    TIMEOUT = "TIMEOUT"
    INVALID_REQUEST = "INVALID_REQUEST"

class ProviderException(Exception):
    def __init__(
        self,
        error_kind: ProviderErrorKind,
        message: str,
        provider: str,
        status_code: Optional[int] = None,
        raw_error: Optional[str] = None
    ):
        super().__init__(message)
        self.error_kind = error_kind
        self.message = message
        self.provider = provider
        self.status_code = status_code
        self.raw_error = raw_error

    def is_provider_level(self) -> bool:
        """Indicates whether this error affects all models for this provider (e.g. invalid credentials or account quota)."""
        return self.error_kind in (ProviderErrorKind.AUTHENTICATION_ERROR, ProviderErrorKind.QUOTA_EXCEEDED)

def classify_provider_error(provider: str, status_code: Optional[int], error_text: str) -> tuple[ProviderErrorKind, str]:
    text_lower = (error_text or "").lower()
    
    # 1. Authentication / Credentials
    if status_code in (401, 403) or "api_key" in text_lower or "unauthorized" in text_lower or "invalid_api_key" in text_lower or "authentication" in text_lower:
        return ProviderErrorKind.AUTHENTICATION_ERROR, f"{provider.capitalize()} authentication failed. Please verify API key configuration."
    
    # 2. Quota / Credits / Billing limit
    if (
        "insufficient_quota" in text_lower
        or "credit_balance_exhausted" in text_lower
        or "quota exceeded" in text_lower
        or "resource_exhausted" in text_lower
        or "generativelanguage.googleapis.com/generate_content_free_tier_requests" in text_lower
        or ("429" in text_lower and ("quota" in text_lower or "credit" in text_lower or "billing" in text_lower or "exceeded your current quota" in text_lower))
    ):
        return ProviderErrorKind.QUOTA_EXCEEDED, f"{provider.capitalize()} quota exceeded (HTTP 429). Please retry later or use another configured provider."
    
    # 3. Rate Limited
    if status_code == 429 or "rate_limit" in text_lower or "rate limit" in text_lower or "too many requests" in text_lower:
        return ProviderErrorKind.RATE_LIMITED, f"{provider.capitalize()} rate limit reached (HTTP 429). Please retry shortly."
        
    # 4. Model Unavailable / Not found
    if status_code == 404 or "model_not_found" in text_lower or "does not exist" in text_lower:
        return ProviderErrorKind.MODEL_UNAVAILABLE, f"Selected model unavailable on provider {provider}."
        
    # 5. Timeout
    if "timeout" in text_lower or "timed out" in text_lower:
        return ProviderErrorKind.TIMEOUT, f"{provider.capitalize()} request timed out."

    # 6. Invalid Request
    if status_code == 400 or "invalid_request" in text_lower:
        return ProviderErrorKind.INVALID_REQUEST, f"Invalid request payload for {provider}."
        
    return ProviderErrorKind.PROVIDER_ERROR, f"{provider.capitalize()} provider error ({status_code or 'UNKNOWN'})."


class ImagePayload(BaseModel):
    mime_type: str = "image/jpeg"
    base64_data: str

class FilePayload(BaseModel):
    mime_type: str
    file_name: str
    base64_data: str
    text_content: Optional[str] = None

class ProviderResult(BaseModel):
    raw_text: str
    parsed_json: Optional[Any] = None
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    latency_ms: float = 0.0
    provider: str
    model: str
    error: Optional[str] = None

class AIProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier (e.g. 'gemini', 'openai', 'groq', 'anthropic')"""
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        """Returns True if the required API key / configuration is set"""
        pass

    @abstractmethod
    def supports_vision(self, model_id: str) -> bool:
        """Whether this model supports image/vision processing"""
        pass

    @abstractmethod
    def supports_json(self, model_id: str) -> bool:
        """Whether this model natively guarantees structured JSON outputs"""
        pass

    @abstractmethod
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
        """Execute inference against the provider API and return structured ProviderResult"""
        pass
