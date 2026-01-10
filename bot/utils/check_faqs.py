"""
Check FAQs in database

Usage:
    python -m bot.utils.check_faqs
"""

import asyncio
from sqlalchemy import select, func

from bot.db.database import init_db, get_db_session
from bot.db.models import FAQ
from bot.utils.logger import get_logger

logger = get_logger(__name__)


async def check_faqs():
    """Check FAQs stored in database"""
    logger.info("Checking FAQs in database...")

    # Initialize database
    await init_db()

    async with get_db_session() as session:
        # Get total count
        total_count = await session.execute(select(func.count(FAQ.id)))
        total = total_count.scalar()

        # Get FAQs with embeddings
        result_with_embeddings = await session.execute(
            select(FAQ).where(FAQ.embedding.isnot(None))
        )
        faqs_with_embeddings = result_with_embeddings.scalars().all()

        # Get FAQs without embeddings
        result_without_embeddings = await session.execute(
            select(FAQ).where(FAQ.embedding.is_(None))
        )
        faqs_without_embeddings = result_without_embeddings.scalars().all()

        # Get all FAQs
        all_result = await session.execute(select(FAQ))
        all_faqs = all_result.scalars().all()

    print("\n" + "="*70)
    print("FAQ DATABASE STATUS")
    print("="*70)
    print(f"Total FAQs: {total}")
    print(f"FAQs with embeddings: {len(faqs_with_embeddings)}")
    print(f"FAQs without embeddings: {len(faqs_without_embeddings)}")
    print("="*70)

    if all_faqs:
        print("\n" + "="*70)
        print("ALL FAQs IN DATABASE:")
        print("="*70)
        for idx, faq in enumerate(all_faqs, 1):
            has_embedding = "[YES]" if faq.embedding else "[NO]"
            embedding_info = f"Embedding: {has_embedding}"
            if faq.embedding:
                embedding_info += f" (dimension: {len(faq.embedding)})"

            print(f"\nFAQ #{faq.id}")
            print(f"  Question: {faq.question[:80]}...")
            print(f"  Answer: {faq.answer[:80]}...")
            print(f"  Category: {faq.category or 'None'}")
            print(f"  {embedding_info}")
            print(f"  Times matched: {faq.times_matched}")
            print(f"  Created at: {faq.created_at}")
    else:
        print("\n[!] NO FAQs FOUND IN DATABASE")
        print("\nTo load FAQs, run:")
        print("  python -m bot.utils.load_faqs")

    print("="*70 + "\n")


async def main():
    """Main entry point"""
    try:
        await check_faqs()
    except Exception as e:
        logger.error(f"Error checking FAQs: {e}", exc_info=True)
        print(f"\n[ERROR] {e}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        raise
