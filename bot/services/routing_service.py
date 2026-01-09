"""
Routing Service

Intelligently routes questions to appropriate mentors.
"""

from dataclasses import dataclass
from typing import List

from sqlalchemy import select

from bot.db.database import get_db_session
from bot.db.models import User, Message, MentorTag
from bot.llm.wrapper import get_llm
from bot.llm.prompts import format_routing_prompt
from bot.utils.config import settings
from bot.utils.exceptions import LLMProviderError
from bot.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class RoutingDecision:
    """Result of routing analysis"""
    complexity: str
    domains: List[str]
    should_tag_mentors: bool
    reason: str
    suggested_mentors: List[str]


class RoutingService:
    """Handles intelligent question routing to mentors"""

    def __init__(self):
        self.llm = get_llm()
        self.mentor_domains = settings.get_mentor_domains()

    async def analyze_question(self, question: str) -> RoutingDecision:
        """
        Analyze question and decide if mentors should be tagged

        Args:
            question: User's question text

        Returns:
            RoutingDecision with analysis and recommendations
        """
        try:
            user_prompt, system_prompt = format_routing_prompt(
                question=question,
                mentor_domains=self.mentor_domains
            )

            response = await self.llm.generate_json(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.5
            )

            decision = RoutingDecision(
                complexity=response.get("complexity", "moderate"),
                domains=response.get("domains", []),
                should_tag_mentors=response.get("should_tag_mentors", False),
                reason=response.get("reason", "No specific reason"),
                suggested_mentors=response.get("suggested_mentors", [])
            )

            logger.info(
                f"Routing analysis: complexity={decision.complexity}, "
                f"should_tag={decision.should_tag_mentors}, "
                f"domains={decision.domains}"
            )

            return decision

        except LLMProviderError as e:
            logger.error(f"Routing analysis failed: {e}")
            return RoutingDecision(
                complexity="unknown",
                domains=[],
                should_tag_mentors=False,
                reason=f"Analysis failed: {e}",
                suggested_mentors=[]
            )

    async def get_mentors_for_domains(
        self,
        domains: List[str]
    ) -> List[User]:
        """
        Get mentor users for specified domains

        Args:
            domains: List of expertise domains

        Returns:
            List of mentor User objects
        """
        mentor_ids = set()
        for domain in domains:
            if domain in self.mentor_domains:
                mentor_ids.update(self.mentor_domains[domain])

        if not mentor_ids:
            logger.warning(f"No mentors found for domains: {domains}")
            return []

        async with get_db_session() as session:
            result = await session.execute(
                select(User).where(
                    User.telegram_id.in_(mentor_ids),
                    User.is_mentor == True
                )
            )
            mentors = list(result.scalars().all())

        logger.info(f"Found {len(mentors)} mentors for domains: {domains}")
        return mentors

    async def tag_mentors(
        self,
        message_id: int,
        mentor_ids: List[int],
        reason: str
    ):
        """
        Record mentor tags in database

        Args:
            message_id: Database message ID
            mentor_ids: List of mentor user IDs to tag
            reason: Reason for tagging (e.g., "computer_vision_expert")
        """
        async with get_db_session() as session:
            for mentor_id in mentor_ids:
                tag = MentorTag(
                    message_id=message_id,
                    mentor_id=mentor_id,
                    reason=reason
                )
                session.add(tag)

            logger.info(f"Tagged {len(mentor_ids)} mentors for message {message_id}")

    def format_mentor_tags(self, mentors: List[User], domains: List[str]) -> str:
        """
        Format mentor tags for Telegram message

        Args:
            mentors: List of mentor users
            domains: Relevant domains

        Returns:
            Formatted string with mentor mentions
        """
        if not mentors:
            return ""

        domain_str = ", ".join(domains) if domains else "this question"

        mentions = []
        for mentor in mentors:
            if mentor.username:
                mentions.append(f"@{mentor.username}")
            else:
                mentions.append(f"[Mentor](tg://user?id={mentor.telegram_id})")

        mentions_str = " ".join(mentions)

        return (
            f"\n\n🔔 This looks like a {domain_str} question. "
            f"Tagging mentors: {mentions_str}"
        )
