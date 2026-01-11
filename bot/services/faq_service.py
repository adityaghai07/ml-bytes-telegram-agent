"""
FAQ Service

Handles FAQ matching using vector similarity search.
"""

from dataclasses import dataclass
from typing import List, Optional

from sqlalchemy import select, text

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
        top_k: int = 1
    ) -> Optional[FAQMatch]:
        """
        Find FAQ most similar to question using database-level cosine similarity

        Args:
            question: User's question
            top_k: Number of top matches to consider (default 1 for best match)

        Returns:
            Best FAQ match if similarity above threshold, else None
        """
        try:
            question_embedding = await self.llm.get_embedding(question)

            # Convert embedding list to PostgreSQL array literal format
            # Using ARRAY constructor is more reliable with SQLAlchemy
            embedding_values = ','.join(str(float(x)) for x in question_embedding)

            # Use raw SQL to calculate cosine similarity in the database
            # This is MUCH faster than loading all FAQs and calculating in Python
            # Note: We use string formatting for the array since it's safe (we control the input)
            # and parameterized binding doesn't work well with array types in raw SQL
            query_str = f"""
                SELECT
                    id,
                    question,
                    answer,
                    category,
                    created_by,
                    created_at,
                    updated_at,
                    times_matched,
                    (
                        -- Cosine similarity formula: (A · B) / (||A|| * ||B||)
                        (
                            SELECT SUM(a * b)
                            FROM unnest(embedding) WITH ORDINALITY AS t1(a, ord)
                            JOIN unnest(ARRAY[{embedding_values}]::float[]) WITH ORDINALITY AS t2(b, ord)
                                ON t1.ord = t2.ord
                        ) / (
                            SQRT((SELECT SUM(a * a) FROM unnest(embedding) AS a)) *
                            SQRT((SELECT SUM(b * b) FROM unnest(ARRAY[{embedding_values}]::float[]) AS b))
                        )
                    ) AS similarity
                FROM faqs
                WHERE embedding IS NOT NULL
                ORDER BY similarity DESC
                LIMIT :limit
            """

            query = text(query_str)

            async with get_db_session() as session:
                result = await session.execute(
                    query,
                    {'limit': top_k}
                )
                row = result.fetchone()

            if not row:
                logger.warning("No FAQs with embeddings found")
                return None

            # Extract values from the result row
            similarity = float(row.similarity) if row.similarity else 0.0

            if similarity >= self.similarity_threshold:
                # Fetch the full FAQ object for the response
                async with get_db_session() as session:
                    faq_result = await session.execute(
                        select(FAQ).where(FAQ.id == row.id)
                    )
                    faq = faq_result.scalar_one()

                logger.info(
                    f"FAQ match found: {faq.id} "
                    f"(similarity: {similarity:.2f})"
                )

                await self._increment_match_count(faq.id)

                return FAQMatch(faq=faq, similarity=similarity)

            logger.info(
                f"No FAQ match above threshold "
                f"(best: {similarity:.2f})"
            )
            return None

        except LLMProviderError as e:
            logger.error(f"FAQ matching failed: {e}")
            return None
        except Exception as e:
            logger.error(f"FAQ matching error: {e}", exc_info=True)
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

    async def _increment_match_count(self, faq_id: int):
        """Increment FAQ match counter"""
        async with get_db_session() as session:
            result = await session.execute(
                select(FAQ).where(FAQ.id == faq_id)
            )
            faq = result.scalar_one_or_none()

            if faq:
                faq.times_matched += 1
