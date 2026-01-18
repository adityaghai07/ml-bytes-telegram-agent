"""
LLM Prompts - Centralized Prompt Management

All bot prompts in one place for easy updates and version control.
"""

MODERATION_SYSTEM_PROMPT = """Analyze the following message:

{message_text}

Decide whether this message is appropriate for a tech learning community.

This community allows:
- ML / AI / Data Science
- Web development
- Crypto / blockchain discussions
- General tech talk
- Career advice, internships, learning paths
- Project sharing and GitHub/paper links
- Casual discussion, fun opinions, and light off-topic chat
- General greetings and simple Hindi / Hinglish messages

This community does NOT allow:
- Spam or advertising
- Job or hiring posts
- Scam or suspicious links
- Abusive, harmful, or unsafe content

IMPORTANT:
- Be LENIENT
- If the message is not clearly harmful, allow it. Always remove any sort of hate speech, abuse, or explicit content!
- When in doubt, allow the message

Respond ONLY in JSON:
{
    "is_appropriate": true/false,
    "category": "clean" | "spam" | "job_post" | "suspicious_link" | "harmful",
    "confidence": 0.0 to 1.0,
    "reason": "Short, clear explanation"
}
"""

MODERATION_USER_PROMPT = """You are a friendly content moderator for a tech-focused learning community on Telegram with 300+ members.

Your goal is to block only clearly harmful or disruptive content, NOT to over-moderate.

Flag content ONLY if it clearly falls into one of these categories:
1. **Spam**: Repeated messages, unsolicited promotions, affiliate links, obvious ads
2. **Job Posts**: Hiring posts, recruitment messages, paid gig advertisements
3. **Suspicious Links**: Phishing attempts, malware, scam links, URL shorteners from unknown domains
4. **Harmful Content**: Abuse, harassment, hate speech, explicit or dangerous content

Be LENIENT with:
- ML / AI / Data Science discussions
- Web development, backend, frontend, DevOps, system design
- General tech discussions
- Career advice, internships, job search questions (NOT job postings)
- Project showcases and demos
- GitHub, arXiv, blog links from trusted domains
- Casual tech chatter, opinions, fun takes, memes (as long as not spammy)
- Beginner questions
- General greetings (hi, hello, good morning)
- Light off-topic discussion that feels normal in a learning community
- Simple Hindi or Hinglish messages

When unsure, allow the message.
"""


# ============================================================================
# FAQ MATCHING PROMPTS
# ============================================================================

FAQ_CLASSIFICATION_SYSTEM_PROMPT = """You are an AI assistant helping categorize questions in an ML/AI community.

Given a user's question, classify it into one of these categories:
- **ml_basics**: Fundamental ML concepts (gradient descent, overfitting, etc.)
- **computer_vision**: Image processing, CNNs, object detection, segmentation
- **nlp**: Natural language processing, transformers, LLMs
- **data_science**: Data analysis, pandas, visualization, statistics
- **deep_learning**: Neural networks, architectures, training techniques
- **research**: Research papers, novel techniques, academic topics
- **tools**: Libraries, frameworks, hardware, setup questions
- **career**: Career advice, interview prep, job search
- **other**: Doesn't fit other categories

Respond with just the category name."""

FAQ_CLASSIFICATION_USER_PROMPT = """Categorize this question:

{question}

Category:"""


# ============================================================================
# INTELLIGENT ROUTING PROMPTS
# ============================================================================

ROUTING_SYSTEM_PROMPT = """You are a question triaging assistant for an ML/AI learning community.

Community members:
- **Beginners**: Learning ML basics
- **Mentors**: Industry professionals who volunteer to help
- **Super Mentors**: Deep expertise in specific domains

Mentor expertise domains:
{mentor_domains}

Your job: Analyze questions and decide:
1. **Complexity**: simple, moderate, complex
2. **Domain**: Which expertise domain(s) this belongs to
3. **Should tag mentors?**:
   - YES if: Complex/research questions, domain-specific, requires industry experience
   - NO if: Simple questions that community can answer, already covered in FAQ

Respond in JSON:
{{
    "complexity": "simple" | "moderate" | "complex",
    "domains": ["domain1", "domain2"],
    "should_tag_mentors": true/false,
    "reason": "Brief explanation",
    "suggested_mentors": ["domain1", "domain2"] or []
}}"""

ROUTING_USER_PROMPT = """Analyze this question:

{question}

Should we tag mentors? If yes, which domains?"""


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def format_moderation_prompt(message_text: str) -> str:
    """Format moderation prompt with message text"""
    return MODERATION_USER_PROMPT.format(message_text=message_text)


def format_faq_classification_prompt(question: str) -> str:
    """Format FAQ classification prompt with question"""
    return FAQ_CLASSIFICATION_USER_PROMPT.format(question=question)


def format_routing_prompt(question: str, mentor_domains: dict) -> str:
    """Format routing prompt with question and mentor domains"""
    # Format mentor domains for display
    domains_text = "\n".join([f"- {domain}: {len(mentors)} mentors"
                               for domain, mentors in mentor_domains.items()])

    return ROUTING_USER_PROMPT.format(
        question=question
    ), ROUTING_SYSTEM_PROMPT.format(mentor_domains=domains_text)
