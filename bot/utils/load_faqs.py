"""
Load FAQs from JSON file into database

Usage:
    python -m bot.utils.load_faqs
"""

import asyncio
import json
from pathlib import Path

from bot.db.database import init_db
from bot.services.faq_service import FAQService
from bot.utils.logger import get_logger

logger = get_logger(__name__)


async def load_faqs_from_json(json_path: str):
    """
    Load FAQs from JSON file and add them to database with embeddings

    Args:
        json_path: Path to FAQ JSON file

    The script will:
    1. Read FAQs from JSON
    2. Generate embeddings for each question
    3. Store in database for RAG functionality
    """
    logger.info(f"Loading FAQs from {json_path}")

    # Initialize database
    await init_db()

    # Read JSON file
    json_file = Path(json_path)
    if not json_file.exists():
        logger.error(f"File not found: {json_path}")
        return

    with open(json_file, 'r', encoding='utf-8') as f:
        faqs_data = json.load(f)

    logger.info(f"Found {len(faqs_data)} FAQs to load")

    # Initialize FAQ service
    faq_service = FAQService()

    # Add each FAQ to database
    success_count = 0
    failed_count = 0

    for idx, faq_data in enumerate(faqs_data, 1):
        question = faq_data.get('question')
        answer = faq_data.get('answer')
        category = faq_data.get('category')  # Optional

        if not question or not answer:
            logger.warning(f"Skipping FAQ {idx}: missing question or answer")
            failed_count += 1
            continue

        try:
            logger.info(f"Adding FAQ {idx}/{len(faqs_data)}: {question[:50]}...")

            faq = await faq_service.add_faq(
                question=question,
                answer=answer,
                category=category,
                created_by=None  # System-added FAQs
            )

            logger.info(f"[SUCCESS] Added FAQ {faq.id}: {question[:50]}...")
            success_count += 1

        except Exception as e:
            logger.error(f"[FAILED] Failed to add FAQ {idx}: {e}")
            failed_count += 1

    logger.info(
        f"\n{'='*60}\n"
        f"FAQ Loading Complete!\n"
        f"[+] Successfully added: {success_count}\n"
        f"[-] Failed: {failed_count}\n"
        f"{'='*60}"
    )


async def main():
    """Main entry point"""
    # Default path to FAQ JSON
    json_path = "data/faq_1.json"

    logger.info("Starting FAQ loader...")
    await load_faqs_from_json(json_path)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        raise
