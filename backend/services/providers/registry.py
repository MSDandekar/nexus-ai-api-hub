from typing import Optional, Dict
from backend.services.providers.base import AIProvider
from backend.services.providers.gemini import GeminiProvider
from backend.services.providers.openai import OpenAIProvider
from backend.services.providers.groq import GroqProvider

class ProviderRegistry:
    def __init__(self):
        self._providers: Dict[str, AIProvider] = {
            "gemini": GeminiProvider(),
            "openai": OpenAIProvider(),
            "groq": GroqProvider(),
        }

    def register(self, provider: AIProvider):
        self._providers[provider.name.lower()] = provider

    def get(self, name: str) -> AIProvider:
        provider = self._providers.get(name.lower())
        if not provider:
            available = ", ".join(self._providers.keys())
            raise ValueError(f"Unknown AI Provider '{name}'. Available: {available}")
        return provider

    def list_providers(self) -> list[dict]:
        return [
            {
                "id": p.name,
                "name": p.name.capitalize(),
                "configured": p.is_configured()
            }
            for p in self._providers.values()
        ]

provider_registry = ProviderRegistry()
