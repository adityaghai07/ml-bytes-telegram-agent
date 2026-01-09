"""Anthropic Claude Provider Implementation"""

import json
from typing import Optional

from anthropic import AsyncAnthropic, AnthropicError

from bot.llm.wrapper import LLMProvider
from bot.utils.exceptions import LLMProviderError
from bot.utils.logger import get_logger

logger = get_logger(__name__)


class ClaudeProvider(LLMProvider):
    """Anthropic Claude provider"""

    def __init__(self, api_key: str, model: Optional[str] = None):
        super().__init__(api_key, model or "claude-3-5-sonnet-20241022")
        self.client = AsyncAnthropic(api_key=api_key)

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 500
    ) -> str:
        try:
            kwargs = {"model": self.model, "max_tokens": max_tokens, "temperature": temperature}
            if system_prompt:
                kwargs["system"] = system_prompt

            response = await self.client.messages.create(
                messages=[{"role": "user", "content": prompt}],
                **kwargs
            )

            return response.content[0].text.strip()

        except AnthropicError as e:
            logger.error(f"Claude API error: {e}")
            raise LLMProviderError(f"Claude API failed: {e}") from e

    async def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7
    ) -> dict:
        try:
            full_system = (system_prompt or "") + "\n\nRespond with valid JSON only."

            response = await self.generate(
                prompt=prompt,
                system_prompt=full_system,
                temperature=temperature,
                max_tokens=1000
            )

            return json.loads(response)

        except (AnthropicError, json.JSONDecodeError) as e:
            logger.error(f"Claude JSON generation error: {e}")
            raise LLMProviderError(f"Claude JSON generation failed: {e}") from e

    async def get_embedding(self, text: str) -> list[float]:
        """
        Claude doesn't have native embeddings API.
        Fallback to a sentence embedding model or use Voyage AI.
        For now, raise an error.
        """
        raise LLMProviderError(
            "Claude provider doesn't support embeddings. "
            "Use OpenAI or implement Voyage AI integration."
        )
