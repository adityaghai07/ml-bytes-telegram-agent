"""
Admin Handler

Handles admin commands for managing the bot.
Commands: /start, /help, /add_faq, /list_faqs, /delete_faq, /stats
"""

from telegram import Update
from telegram.ext import ContextTypes

from bot.db.database import get_db_session
from bot.db.models import User, FAQ, ModerationLog
from bot.services.faq_service import FAQService
from bot.utils.config import settings
from bot.utils.logger import get_logger
from sqlalchemy import select, func

logger = get_logger(__name__)


faq_service = FAQService()


def is_admin(user_id: int) -> bool:
    """Check if user is admin"""
    return user_id in settings.get_admin_ids()


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    await update.message.reply_text(
        "🤖 **ML Bytes Community Bot**\n\n"
        "I help manage this community by:\n"
        "• Filtering spam and inappropriate content\n"
        "• Answering common questions automatically\n"
        "• Routing complex questions to mentors\n\n"
        "For admin commands, use /help",
        parse_mode="Markdown"
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    user_id = update.effective_user.id

    if is_admin(user_id):
        help_text = (
            "🛠️ **Admin Commands**\n\n"
            "**FAQ Management:**\n"
            "• /add_faq - Add new FAQ (format: /add_faq question | answer | category)\n"
            "• /list_faqs - List all FAQs\n"
            "• /delete_faq <id> - Delete FAQ by ID\n\n"
            "**Statistics:**\n"
            "• /stats - View bot statistics\n\n"
            "**Info:**\n"
            "• /start - Bot introduction\n"
            "• /help - This help message"
        )
    else:
        help_text = (
            "ℹ️ **Available Commands**\n\n"
            "• /start - Bot introduction\n"
            "• /help - This help message\n\n"
            "For questions, just send a message to the group!"
        )

    await update.message.reply_text(help_text, parse_mode="Markdown")


async def cmd_add_faq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /add_faq command

    Format: /add_faq question | answer | category
    Example: /add_faq What is ML? | Machine Learning is... | ml_basics
    """
    user_id = update.effective_user.id

    if not is_admin(user_id):
        await update.message.reply_text("⛔ This command is only available to admins.")
        return

    if not context.args:
        await update.message.reply_text(
            "❌ **Usage:** /add_faq question | answer | category\n\n"
            "**Example:**\n"
            "/add_faq What is gradient descent? | Gradient descent is... | ml_basics",
            parse_mode="Markdown"
        )
        return

    try:
        full_text = " ".join(context.args)
        parts = [p.strip() for p in full_text.split("|")]

        if len(parts) < 2:
            await update.message.reply_text(
                "❌ Please provide at least question and answer separated by |"
            )
            return

        question = parts[0]
        answer = parts[1]
        category = parts[2] if len(parts) > 2 else None

        async with get_db_session() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == user_id)
            )
            user = result.scalar_one_or_none()
            user_db_id = user.id if user else None

        faq = await faq_service.add_faq(
            question=question,
            answer=answer,
            category=category,
            created_by=user_db_id
        )

        await update.message.reply_text(
            f"✅ FAQ added successfully!\n\n"
            f"**ID:** {faq.id}\n"
            f"**Question:** {question}\n"
            f"**Category:** {category or 'None'}",
            parse_mode="Markdown"
        )

        logger.info(f"Admin {user_id} added FAQ {faq.id}")

    except Exception as e:
        logger.error(f"Error adding FAQ: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Error adding FAQ: {str(e)}")


async def cmd_list_faqs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /list_faqs command"""
    user_id = update.effective_user.id

    if not is_admin(user_id):
        await update.message.reply_text("⛔ This command is only available to admins.")
        return

    try:
        faqs = await faq_service.get_all_faqs()

        if not faqs:
            await update.message.reply_text("📭 No FAQs found.")
            return

        response = "📚 **All FAQs**\n\n"

        for faq in faqs[:20]:
            response += (
                f"**ID:** {faq.id}\n"
                f"**Q:** {faq.question[:100]}...\n"
                f"**Category:** {faq.category or 'None'}\n"
                f"**Matches:** {faq.times_matched}\n\n"
            )

        if len(faqs) > 20:
            response += f"\n_Showing 20 of {len(faqs)} FAQs_"

        await update.message.reply_text(response, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Error listing FAQs: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Error: {str(e)}")


async def cmd_delete_faq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /delete_faq command

    Format: /delete_faq <id>
    Example: /delete_faq 5
    """
    user_id = update.effective_user.id

    if not is_admin(user_id):
        await update.message.reply_text("⛔ This command is only available to admins.")
        return

    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text(
            "❌ **Usage:** /delete_faq <id>\n\n"
            "**Example:** /delete_faq 5",
            parse_mode="Markdown"
        )
        return

    try:
        faq_id = int(context.args[0])
        deleted = await faq_service.delete_faq(faq_id)

        if deleted:
            await update.message.reply_text(f"✅ FAQ {faq_id} deleted successfully.")
            logger.info(f"Admin {user_id} deleted FAQ {faq_id}")
        else:
            await update.message.reply_text(f"❌ FAQ {faq_id} not found.")

    except Exception as e:
        logger.error(f"Error deleting FAQ: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Error: {str(e)}")


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stats command - show bot statistics"""
    user_id = update.effective_user.id

    if not is_admin(user_id):
        await update.message.reply_text("⛔ This command is only available to admins.")
        return

    try:
        async with get_db_session() as session:
            user_count = await session.scalar(select(func.count(User.id)))
            faq_count = await session.scalar(select(func.count(FAQ.id)))
            moderation_count = await session.scalar(select(func.count(ModerationLog.id)))

            deleted_count = await session.scalar(
                select(func.count(ModerationLog.id)).where(
                    ModerationLog.action == "deleted"
                )
            )

        stats_text = (
            "📊 **Bot Statistics**\n\n"
            f"👥 **Total Users:** {user_count}\n"
            f"📚 **Total FAQs:** {faq_count}\n"
            f"🛡️ **Moderation Checks:** {moderation_count}\n"
            f"🗑️ **Messages Deleted:** {deleted_count}\n\n"
            f"🤖 **LLM Provider:** {settings.LLM_PROVIDER}\n"
            f"🌍 **Environment:** {settings.ENVIRONMENT}"
        )

        await update.message.reply_text(stats_text, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Error getting stats: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Error: {str(e)}")
