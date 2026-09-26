from abc import ABC, abstractmethod
from typing import Optional, Any
from pydantic import BaseModel, Field

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
