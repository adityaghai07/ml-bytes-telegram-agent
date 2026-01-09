"""
Moderation Service

Checks messages for spam, job posts, and suspicious links.
"""

import json
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import select

from bot.db.database import get_db_session
from bot.db.models import ModerationLog, User, Message
from bot.llm.wrapper import get_llm
from bot.llm.prompts import MODERATION_SYSTEM_PROMPT, format_moderation_prompt
from bot.utils.config import settings
from bot.utils.exceptions import ModerationError, LLMProviderError
from bot.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ModerationResult:
    """Result of content moderation check"""
    is_appropriate: bool
    category: str
    confidence: float
    reason: str


class ModerationService:
    """Handles content moderation using LLM"""

    def __init__(self):
        self.llm = get_llm()
        self.threshold = settings.MODERATION_CONFIDENCE_THRESHOLD

    async def check_content(
        self,
        message_text: str,
        user_id: int,
        telegram_message_id: int
    ) -> ModerationResult:
        """
        Check if message content is appropriate

        Args:
            message_text: The message text to check
            user_id: Database user ID
            telegram_message_id: Telegram message ID

        Returns:
            ModerationResult with decision and reasoning
        """
        try:
            prompt = format_moderation_prompt(message_text)

            response = await self.llm.generate_json(
                prompt=prompt,
                system_prompt=MODERATION_SYSTEM_PROMPT,
                temperature=0.3
            )

            result = ModerationResult(
                is_appropriate=response.get("is_appropriate", True),
                category=response.get("category", "clean"),
                confidence=response.get("confidence", 0.5),
                reason=response.get("reason", "No specific reason")
            )

            await self._log_moderation(
                user_id=user_id,
                telegram_message_id=telegram_message_id,
                message_text=message_text,
                result=result
            )

            logger.info(
                f"Moderation check: user={user_id}, "
                f"category={result.category}, "
                f"confidence={result.confidence}"
            )

            return result

        except LLMProviderError as e:
            logger.error(f"LLM moderation failed: {e}")
            raise ModerationError(f"Moderation check failed: {e}") from e

    async def _log_moderation(
        self,
        user_id: int,
        telegram_message_id: int,
        message_text: str,
        result: ModerationResult
    ):
        """Log moderation decision to database"""
        try:
            async with get_db_session() as session:
                message_result = await session.execute(
                    select(Message).where(
                        Message.user_id == user_id,
                        Message.telegram_message_id == telegram_message_id
                    )
                )
                message = message_result.scalar_one_or_none()

                action = "deleted" if not result.is_appropriate else "allowed"

                log_entry = ModerationLog(
                    message_id=message.id if message else None,
                    user_id=user_id,
                    action=action,
                    reason=result.category,
                    confidence=result.confidence,
                    message_text=message_text,
                    llm_provider=settings.LLM_PROVIDER
                )

                session.add(log_entry)

        except Exception as e:
            logger.error(f"Failed to log moderation: {e}")

    def should_delete(self, result: ModerationResult) -> bool:
        """Decide if message should be deleted based on moderation result"""
        return (
            not result.is_appropriate
            and result.confidence >= self.threshold
            and result.category != "clean"
        )
