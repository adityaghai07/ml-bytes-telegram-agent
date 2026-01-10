"""
Sync Mentors from .env to Database

Marks users as mentors and sets their expertise domains based on MENTOR_DOMAINS config.

Usage:
    python -m bot.utils.sync_mentors
"""

import asyncio
from sqlalchemy import select

from bot.db.database import init_db, get_db_session
from bot.db.models import User
from bot.utils.config import settings
from bot.utils.logger import get_logger

logger = get_logger(__name__)


async def sync_mentors():
    """Sync mentor configuration from .env to database"""
    logger.info("Syncing mentors from configuration to database...")

    # Initialize database
    await init_db()

    # Get mentor domains from .env
    mentor_domains = settings.get_mentor_domains()
    logger.info(f"Mentor domains from config: {mentor_domains}")

    # Collect all unique mentor IDs and their domains
    mentor_info = {}  # telegram_id -> list of domains
    for domain, telegram_ids in mentor_domains.items():
        for telegram_id in telegram_ids:
            if telegram_id not in mentor_info:
                mentor_info[telegram_id] = []
            mentor_info[telegram_id].append(domain)

    if not mentor_info:
        logger.warning("No mentors configured in MENTOR_DOMAINS")
        print("\n[!] No mentors found in .env configuration")
        print("Please configure MENTOR_DOMAINS in your .env file")
        return

    logger.info(f"Found {len(mentor_info)} unique mentors in configuration")

    # Update users in database
    updated_count = 0
    not_found_count = 0

    async with get_db_session() as session:
        for telegram_id, domains in mentor_info.items():
            # Find user in database
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()

            if user:
                # Update mentor status and domains
                user.is_mentor = True
                user.expertise_domains = domains

                logger.info(
                    f"Updated user {user.username or user.telegram_id}: "
                    f"is_mentor=True, domains={domains}"
                )
                updated_count += 1
            else:
                logger.warning(
                    f"User with telegram_id {telegram_id} not found in database. "
                    f"They need to join the group first."
                )
                not_found_count += 1

    # Print summary
    print("\n" + "="*70)
    print("MENTOR SYNC COMPLETE")
    print("="*70)
    print(f"Total mentors in config: {len(mentor_info)}")
    print(f"[+] Successfully updated: {updated_count}")
    print(f"[-] Not found in database: {not_found_count}")
    print("="*70)

    if not_found_count > 0:
        print("\n[!] Some mentors were not found in the database.")
        print("They need to join/interact with the bot first.")
        print("After they join, run this script again.")

    # Show updated mentors
    if updated_count > 0:
        print("\n" + "="*70)
        print("UPDATED MENTORS:")
        print("="*70)
        async with get_db_session() as session:
            result = await session.execute(
                select(User).where(User.is_mentor == True)
            )
            mentors = result.scalars().all()

            for mentor in mentors:
                domains_str = ", ".join(mentor.expertise_domains) if mentor.expertise_domains else "None"
                print(f"\n  Mentor ID: {mentor.telegram_id}")
                print(f"  Username: @{mentor.username or 'N/A'}")
                print(f"  Name: {mentor.first_name or 'N/A'}")
                print(f"  Domains: {domains_str}")
        print("="*70)


async def main():
    """Main entry point"""
    try:
        await sync_mentors()
    except Exception as e:
        logger.error(f"Error syncing mentors: {e}", exc_info=True)
        print(f"\n[ERROR] {e}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        raise
