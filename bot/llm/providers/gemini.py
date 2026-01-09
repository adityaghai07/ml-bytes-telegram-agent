"""Google Gemini Provider Implementation"""

import json
from typing import Optional

import google.generativeai as genai
from google.api_core import exceptions as google_exceptions

from bot.llm.wrapper import LLMProvider
from bot.utils.exceptions import LLMProviderError
from bot.utils.logger import get_logger

logger = get_logger(__name__)


class GeminiProvider(LLMProvider):
    """Google Gemini provider"""

    def __init__(self, api_key: str, model: Optional[str] = None):
        super().__init__(api_key, model or "gemini-1.5-flash")
        genai.configure(api_key=api_key)
        self.model_instance = genai.GenerativeModel(self.model)

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 500
    ) -> str:
        try:
            full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt

            generation_config = genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens
            )

            response = await self.model_instance.generate_content_async(
                full_prompt,
                generation_config=generation_config
            )

            return response.text.strip()

        except google_exceptions.GoogleAPIError as e:
            logger.error(f"Gemini API error: {e}")
            raise LLMProviderError(f"Gemini API failed: {e}") from e

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

        except (google_exceptions.GoogleAPIError, json.JSONDecodeError) as e:
            logger.error(f"Gemini JSON generation error: {e}")
            raise LLMProviderError(f"Gemini JSON generation failed: {e}") from e

    async def get_embedding(self, text: str) -> list[float]:
        try:
            result = genai.embed_content(
                model="models/embedding-001",
                content=text,
                task_type="retrieval_document"
            )
            return result['embedding']

        except google_exceptions.GoogleAPIError as e:
            logger.error(f"Gemini embedding error: {e}")
            raise LLMProviderError(f"Gemini embedding failed: {e}") from e
