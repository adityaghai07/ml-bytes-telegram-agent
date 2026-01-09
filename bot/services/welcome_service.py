"""
Welcome Service

Handles new member onboarding and welcome messages.
"""

from sqlalchemy import select, func

from bot.db.database import get_db_session
from bot.db.models import User
from bot.llm.prompts import format_welcome_message
from bot.utils.logger import get_logger

logger = get_logger(__name__)


class WelcomeService:
    """Handles new member welcome flow"""

    async def create_or_update_user(
        self,
        telegram_id: int,
        username: str | None,
        first_name: str | None,
        last_name: str | None
    ) -> User:
        """
        Create new user or update existing user info

        Args:
            telegram_id: Telegram user ID
            username: Telegram username
            first_name: User's first name
            last_name: User's last name

        Returns:
            User object
        """
        async with get_db_session() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()

            if user:
                user.username = username
                user.first_name = first_name
                user.last_name = last_name
                logger.info(f"Updated user: {telegram_id}")
            else:
                user = User(
                    telegram_id=telegram_id,
                    username=username,
                    first_name=first_name,
                    last_name=last_name
                )
                session.add(user)
                logger.info(f"Created new user: {telegram_id}")

            await session.flush()
            await session.refresh(user)
            return user

    async def get_welcome_message(self, first_name: str | None) -> str:
        """
        Generate welcome message for new member

        Args:
            first_name: User's first name

        Returns:
            Formatted welcome message
        """
        member_count = await self._get_member_count()

        return format_welcome_message(
            first_name=first_name or "there",
            member_count=member_count
        )

    async def _get_member_count(self) -> int:
        """Get total number of community members"""
        async with get_db_session() as session:
            result = await session.execute(
                select(func.count(User.id))
            )
            count = result.scalar()
            return count or 0
