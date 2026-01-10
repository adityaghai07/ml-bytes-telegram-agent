"""
Main Bot Entry Point

Initializes and runs the Telegram bot.
"""

import asyncio
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ChatMemberHandler,
    filters,
)

from bot.db.database import init_db, close_db
from bot.handlers import message, member, admin
from bot.utils.config import settings
from bot.utils.logger import get_logger

logger = get_logger(__name__)


async def post_init(application: Application):
    """
    Initialize bot after startup

    Called once when bot starts up.
    Sets up database and performs any necessary initialization.
    """
    logger.info("Initializing bot...")

    try:
        await init_db()
        logger.info("Database initialized successfully")

        bot_info = await application.bot.get_me()
        logger.info(f"Bot started: @{bot_info.username} (ID: {bot_info.id})")

    except Exception as e:
        logger.error(f"Initialization error: {e}", exc_info=True)
        raise


async def post_shutdown(application: Application):
    """
    Cleanup on shutdown

    Called when bot is shutting down.
    Closes database connections and performs cleanup.
    """
    logger.info("Shutting down bot...")

    try:
        await close_db()
        logger.info("Database connections closed")

    except Exception as e:
        logger.error(f"Shutdown error: {e}", exc_info=True)


def main():
    """
    Main function - builds and runs the bot

    Sets up:
    1. Application with bot token
    2. Command handlers (/start, /help, etc.)
    3. Message handlers (text messages)
    4. Member handlers (joins/leaves)
    5. Error handler
    """
    logger.info("Starting ML Bytes Telegram Bot...")

    application = (
        Application.builder()
        .token(settings.TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    application.add_handler(CommandHandler("start", admin.cmd_start))
    application.add_handler(CommandHandler("help", admin.cmd_help))
    application.add_handler(CommandHandler("add_faq", admin.cmd_add_faq))
    application.add_handler(CommandHandler("list_faqs", admin.cmd_list_faqs))
    application.add_handler(CommandHandler("delete_faq", admin.cmd_delete_faq))
    application.add_handler(CommandHandler("stats", admin.cmd_stats))

    application.add_handler(
        ChatMemberHandler(member.handle_new_member, ChatMemberHandler.CHAT_MEMBER)
    )

    application.add_handler(
        MessageHandler(
            filters.StatusUpdate.NEW_CHAT_MEMBERS,
            member.handle_new_member
        )
    )

    application.add_handler(
        MessageHandler(
            filters.StatusUpdate.LEFT_CHAT_MEMBER,
            member.handle_left_member
        )
    )

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            message.handle_message
        )
    )

    application.add_error_handler(error_handler)

    logger.info("Bot handlers registered. Starting polling...")

    application.run_polling(
        allowed_updates=["message", "chat_member"],
        drop_pending_updates=True
    )


async def error_handler(update: object, context):
    """Global error handler for unhandled exceptions"""
    logger.error(f"Unhandled exception: {context.error}", exc_info=context.error)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        raise
