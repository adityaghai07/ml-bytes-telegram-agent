"""
FAQ Service

Handles FAQ matching using vector similarity search.
"""

import numpy as np
from dataclasses import dataclass
from typing import List, Optional

from sqlalchemy import select

from bot.db.database import get_db_session
from bot.db.models import FAQ
from bot.llm.wrapper import get_llm
from bot.utils.config import settings
from bot.utils.exceptions import LLMProviderError
from bot.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class FAQMatch:
    """FAQ search result"""
    faq: FAQ
    similarity: float


class FAQService:
    """Handles FAQ storage and similarity matching"""

    def __init__(self):
        self.llm = get_llm()
        self.similarity_threshold = settings.FAQ_SIMILARITY_THRESHOLD

    async def find_matching_faq(
        self,
        question: str,
        top_k: int = 3
    ) -> Optional[FAQMatch]:
        """
        Find FAQ most similar to question

        Args:
            question: User's question
            top_k: Number of top matches to consider

        Returns:
            Best FAQ match if similarity above threshold, else None
        """
        try:
            question_embedding = await self.llm.get_embedding(question)

            async with get_db_session() as session:
                result = await session.execute(
                    select(FAQ).where(FAQ.embedding.isnot(None))
                )
                faqs = result.scalars().all()

            if not faqs:
                logger.warning("No FAQs with embeddings found")
                return None

            matches = []
            for faq in faqs:
                similarity = self._cosine_similarity(
                    question_embedding,
                    faq.embedding
                )
                matches.append(FAQMatch(faq=faq, similarity=similarity))

            matches.sort(key=lambda x: x.similarity, reverse=True)
            best_match = matches[0]

            if best_match.similarity >= self.similarity_threshold:
                logger.info(
                    f"FAQ match found: {best_match.faq.id} "
                    f"(similarity: {best_match.similarity:.2f})"
                )

                await self._increment_match_count(best_match.faq.id)

                return best_match

            logger.info(
                f"No FAQ match above threshold "
                f"(best: {best_match.similarity:.2f})"
            )
            return None

        except LLMProviderError as e:
            logger.error(f"FAQ matching failed: {e}")
            return None

    async def add_faq(
        self,
        question: str,
        answer: str,
        category: str | None = None,
        created_by: int | None = None
    ) -> FAQ:
        """
        Add new FAQ with embedding

        Args:
            question: FAQ question
            answer: FAQ answer
            category: Optional category
            created_by: User ID who created it

        Returns:
            Created FAQ object
        """
        try:
            embedding = await self.llm.get_embedding(question)

            async with get_db_session() as session:
                faq = FAQ(
                    question=question,
                    answer=answer,
                    category=category,
                    embedding=embedding,
                    created_by=created_by
                )
                session.add(faq)
                await session.flush()
                await session.refresh(faq)

                logger.info(f"Created FAQ: {faq.id}")
                return faq

        except LLMProviderError as e:
            logger.error(f"Failed to create FAQ: {e}")
            raise

    async def get_all_faqs(self) -> List[FAQ]:
        """Get all FAQs"""
        async with get_db_session() as session:
            result = await session.execute(select(FAQ))
            return list(result.scalars().all())

    async def delete_faq(self, faq_id: int) -> bool:
        """Delete FAQ by ID"""
        async with get_db_session() as session:
            result = await session.execute(
                select(FAQ).where(FAQ.id == faq_id)
            )
            faq = result.scalar_one_or_none()

            if faq:
                await session.delete(faq)
                logger.info(f"Deleted FAQ: {faq_id}")
                return True

            return False

    def _cosine_similarity(
        self,
        vec1: List[float],
        vec2: List[float]
    ) -> float:
        """
        Calculate cosine similarity between two vectors

        Cosine similarity = (A · B) / (||A|| * ||B||)
        Returns value between 0 and 1 (1 = identical)
        """
        a = np.array(vec1)
        b = np.array(vec2)

        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return float(dot_product / (norm_a * norm_b))

    async def _increment_match_count(self, faq_id: int):
        """Increment FAQ match counter"""
        async with get_db_session() as session:
            result = await session.execute(
                select(FAQ).where(FAQ.id == faq_id)
            )
            faq = result.scalar_one_or_none()

            if faq:
                faq.times_matched += 1
