"""
Message Handler

Processes all text messages in the group.
Flow: Moderation → FAQ matching → Intelligent routing
"""

from telegram import Update
from telegram.ext import ContextTypes

from bot.db.database import get_db_session
from bot.db.models import User, Message
from bot.services.moderation_service import ModerationService
from bot.services.faq_service import FAQService
from bot.services.routing_service import RoutingService
from bot.utils.logger import get_logger
from bot.utils.config import settings

logger = get_logger(__name__)


moderation_service = ModerationService()
faq_service = FAQService()
routing_service = RoutingService()


def _is_admin(telegram_id: int) -> bool:
    """Check if user is admin based on config"""
    return telegram_id in settings.get_admin_ids()


def _is_mentor(telegram_id: int) -> bool:
    """Check if user is mentor based on config"""
    mentor_domains = settings.get_mentor_domains()
    return any(telegram_id in mentor_ids for mentor_ids in mentor_domains.values())


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Main message handler

    Processes messages through multiple stages:
    1. Moderation check (delete if spam/inappropriate)
    2. FAQ matching (auto-respond if match found)
    3. Intelligent routing (tag mentors if needed)
    """
    if not update.message or not update.message.text:
        return

    message = update.message
    text = message.text
    user = message.from_user

    logger.info(f"Message from {user.id}: {text[:50]}...")

    try:
        db_user = await _get_or_create_user(user)
        db_message = await _store_message(db_user.id, message.message_id, text)

        # Check if user is admin or mentor - they bypass moderation, FAQ, and routing
        is_elevated_user = db_user.is_admin or db_user.is_mentor

        if is_elevated_user:
            logger.info(f"Skipping moderation/FAQ/routing for {'admin' if db_user.is_admin else 'mentor'} {user.id}")
            return

        should_delete = await _check_moderation(text, db_user.id, message.message_id)
        if should_delete:
            await message.delete()
            logger.info(f"Deleted message from user {user.id}")
            return

        faq_match = await faq_service.find_matching_faq(text)
        if faq_match:
            # Use plain text for FAQ responses to avoid Markdown parsing issues with URLs
            await message.reply_text(
                f"💡 FAQ Match\n\n"
                f"Q: {faq_match.faq.question}\n\n"
                f"A: {faq_match.faq.answer}"
            )
            logger.info(f"Replied with FAQ {faq_match.faq.id}")
            return

        routing_decision = await routing_service.analyze_question(text)

        if routing_decision.should_tag_mentors and routing_decision.domains:
            mentors = await routing_service.get_mentors_for_domains(
                routing_decision.domains
            )

            if mentors:
                tag_message = routing_service.format_mentor_tags(
                    mentors,
                    routing_decision.domains
                )
                await message.reply_text(tag_message, parse_mode="Markdown")

                await routing_service.tag_mentors(
                    message_id=db_message.id,
                    mentor_ids=[m.id for m in mentors],
                    reason=", ".join(routing_decision.domains)
                )

                logger.info(f"Tagged {len(mentors)} mentors for message {db_message.id}")

    except Exception as e:
        logger.error(f"Error handling message: {e}", exc_info=True)


async def _get_or_create_user(telegram_user) -> User:
    """Get user from DB or create if doesn't exist"""
    async with get_db_session() as session:
        from sqlalchemy import select
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_user.id)
        )
        user = result.scalar_one_or_none()

        # Check current role status from config
        is_admin = _is_admin(telegram_user.id)
        is_mentor = _is_mentor(telegram_user.id)

        if not user:
            # Create new user with role flags
            user = User(
                telegram_id=telegram_user.id,
                username=telegram_user.username,
                first_name=telegram_user.first_name,
                last_name=telegram_user.last_name,
                is_admin=is_admin,
                is_mentor=is_mentor
            )
            session.add(user)
            await session.flush()
            await session.refresh(user)
        else:
            # Update role flags if they've changed in config
            if user.is_admin != is_admin or user.is_mentor != is_mentor:
                user.is_admin = is_admin
                user.is_mentor = is_mentor
                await session.flush()
                await session.refresh(user)

        return user


async def _store_message(user_id: int, telegram_message_id: int, text: str) -> Message:
    """Store message in database"""
    async with get_db_session() as session:
        message = Message(
            user_id=user_id,
            telegram_message_id=telegram_message_id,
            text=text
        )
        session.add(message)
        await session.flush()
        await session.refresh(message)
        return message


async def _check_moderation(text: str, user_id: int, telegram_message_id: int) -> bool:
    """Check if message should be deleted"""
    result = await moderation_service.check_content(
        message_text=text,
        user_id=user_id,
        telegram_message_id=telegram_message_id
    )
    return moderation_service.should_delete(result)


def _escape_markdown(text: str) -> str:
    """
    Escape Markdown special characters

    Args:
        text: Text to escape

    Returns:
        Escaped text safe for Markdown parsing
    """
    # Markdown special characters that need escaping
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']

    for char in special_chars:
        text = text.replace(char, f'\\{char}')

    return text
