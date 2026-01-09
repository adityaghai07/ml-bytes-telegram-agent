"""OpenAI Provider Implementation"""

import json
from typing import Optional

from openai import AsyncOpenAI
from openai import OpenAIError

from bot.llm.wrapper import LLMProvider
from bot.utils.exceptions import LLMProviderError
from bot.utils.logger import get_logger

logger = get_logger(__name__)


class OpenAIProvider(LLMProvider):
    """OpenAI GPT provider"""

    def __init__(self, api_key: str, model: Optional[str] = None):
        super().__init__(api_key, model or "gpt-4o-mini")
        self.client = AsyncOpenAI(api_key=api_key)

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 500
    ) -> str:
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )

            return response.choices[0].message.content.strip()

        except OpenAIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise LLMProviderError(f"OpenAI API failed: {e}") from e

    async def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7
    ) -> dict:
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                response_format={"type": "json_object"}
            )

            content = response.choices[0].message.content.strip()
            return json.loads(content)

        except (OpenAIError, json.JSONDecodeError) as e:
            logger.error(f"OpenAI JSON generation error: {e}")
            raise LLMProviderError(f"OpenAI JSON generation failed: {e}") from e

    async def get_embedding(self, text: str) -> list[float]:
        try:
            response = await self.client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            return response.data[0].embedding

        except OpenAIError as e:
            logger.error(f"OpenAI embedding error: {e}")
            raise LLMProviderError(f"OpenAI embedding failed: {e}") from e
