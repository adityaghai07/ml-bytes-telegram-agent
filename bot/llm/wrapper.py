"""
LLM Wrapper - Provider-Agnostic Interface

Abstraction layer for switching between OpenAI, Claude, and Gemini.

Usage:
    llm = get_llm()
    response = await llm.generate("What is ML?")
"""

from abc import ABC, abstractmethod
from typing import Optional

from bot.utils.config import settings
from bot.utils.exceptions import LLMProviderError
from bot.utils.logger import get_logger

logger = get_logger(__name__)


class LLMProvider(ABC):
    """Abstract base class for LLM providers (OpenAI, Claude, Gemini)"""

    def __init__(self, api_key: str, model: Optional[str] = None):
        self.api_key = api_key
        self.model = model
        logger.info(f"Initialized {self.__class__.__name__} with model {model}")

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 500
    ) -> str:
        """Generate text response from prompt"""
        pass

    @abstractmethod
    async def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7
    ) -> dict:
        """Generate JSON response from prompt"""
        pass

    @abstractmethod
    async def get_embedding(self, text: str) -> list[float]:
        """Get vector embedding for text (for FAQ similarity matching)"""
        pass


def get_llm_provider() -> LLMProvider:
    """Factory function to get LLM provider based on settings"""
    provider_name = settings.LLM_PROVIDER.lower()
    api_key = settings.get_llm_api_key()

    if provider_name == "openai":
        from bot.llm.providers.openai import OpenAIProvider
        return OpenAIProvider(api_key)
    elif provider_name == "claude":
        from bot.llm.providers.claude import ClaudeProvider
        return ClaudeProvider(api_key)
    elif provider_name == "gemini":
        from bot.llm.providers.gemini import GeminiProvider
        return GeminiProvider(api_key)
    else:
        raise ValueError(
            f"Unknown LLM provider: {provider_name}. "
            f"Must be one of: openai, claude, gemini"
        )


_llm_provider: Optional[LLMProvider] = None


def get_llm() -> LLMProvider:
    """Get global LLM provider instance (singleton)"""
    global _llm_provider
    if _llm_provider is None:
        _llm_provider = get_llm_provider()
    return _llm_provider
