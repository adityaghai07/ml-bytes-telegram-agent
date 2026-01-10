"""
Member Handler

Handles new member joins - silently creates user records for tracking.
Users should read the pinned message for guidelines.
"""

from telegram import Update
from telegram.ext import ContextTypes

from bot.services.welcome_service import WelcomeService
from bot.utils.logger import get_logger

logger = get_logger(__name__)


welcome_service = WelcomeService()


async def handle_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle new member joins - silently create user record

    Process:
    - Creates/updates user in database for tracking
    - No welcome message (rely on pinned message in group)
    - Completely silent - no group spam
    """
    if not update.message or not update.message.new_chat_members:
        return

    for new_member in update.message.new_chat_members:
        if new_member.is_bot:
            continue

        logger.info(f"New member joined: {new_member.id} (@{new_member.username})")

        try:
            # Create user record silently (no group message)
            await welcome_service.create_or_update_user(
                telegram_id=new_member.id,
                username=new_member.username,
                first_name=new_member.first_name,
                last_name=new_member.last_name
            )

            logger.info(f"Created/updated user record for {new_member.id} - no welcome message sent")

        except Exception as e:
            logger.error(f"Error creating user record for {new_member.id}: {e}", exc_info=True)


# NOTE: Guidelines acceptance handler removed - using pinned message instead
# Uncomment this section if you want to re-enable the guidelines acceptance flow
# (requires converting group to supergroup and re-registering the handler in main.py)

# async def handle_guidelines_acceptance(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     """
#     Handle when user clicks "I Accept Guidelines" button
#
#     Verifies the correct user clicked the button, then:
#     1. Grants full posting permissions
#     2. Updates the message to show acceptance confirmation
#     3. Logs the acceptance event
#     """
#     query = update.callback_query
#     await query.answer()
#
#     # Parse callback data: "accept_guidelines:123456789"
#     data_parts = query.data.split(":")
#     if len(data_parts) != 2 or data_parts[0] != "accept_guidelines":
#         return
#
#     expected_user_id = int(data_parts[1])
#     actual_user_id = query.from_user.id
#
#     # Security: Verify the person clicking is the new member (not someone else)
#     if actual_user_id != expected_user_id:
#         await query.answer("❌ This button is not for you!", show_alert=True)
#         return
#
#     try:
#         from telegram import ChatPermissions
#
#         # Grant full posting permissions to the new member
#         await context.bot.restrict_chat_member(
#             chat_id=query.message.chat_id,
#             user_id=actual_user_id,
#             permissions=ChatPermissions(
#                 can_send_messages=True,
#                 can_send_audios=True,
#                 can_send_documents=True,
#                 can_send_photos=True,
#                 can_send_videos=True,
#                 can_send_video_notes=True,
#                 can_send_voice_notes=True,
#                 can_send_polls=True,
#                 can_send_other_messages=True,
#                 can_add_web_page_previews=True,
#             )
#         )
#
#         # Edit the message to show acceptance (keeps group clean)
#         await query.edit_message_text(
#             f"✅ {query.from_user.first_name} has accepted the guidelines and can now chat!",
#             parse_mode="Markdown"
#         )
#
#         logger.info(f"User {actual_user_id} accepted guidelines and was granted permissions")
#
#     except Exception as e:
#         logger.error(f"Error granting permissions to {actual_user_id}: {e}", exc_info=True)
#         await query.answer("❌ Error granting permissions. Please contact an admin.", show_alert=True)


async def handle_left_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle member leaving the group

    Currently just logs the event. Could be extended to:
    - Update user status in database
    - Send goodbye message
    - Archive user data
    """
    if not update.message or not update.message.left_chat_member:
        return

    left_member = update.message.left_chat_member

    if not left_member.is_bot:
        logger.info(f"Member left: {left_member.id} (@{left_member.username})")
