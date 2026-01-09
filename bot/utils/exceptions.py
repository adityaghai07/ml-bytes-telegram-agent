"""
Custom Exceptions

Define custom exception classes for better error handling.
This makes it easier to catch specific errors and handle them appropriately.

Example:
    try:
        result = await llm.generate(prompt)
    except LLMProviderError as e:
        logger.error(f"LLM failed: {e}")
        # Fallback logic here
"""


class BotBaseException(Exception):
    """Base exception for all bot errors"""
    pass


class LLMProviderError(BotBaseException):
    """Raised when LLM API call fails"""
    pass


class DatabaseError(BotBaseException):
    """Raised when database operation fails"""
    pass


class ConfigurationError(BotBaseException):
    """Raised when configuration is invalid"""
    pass


class ModerationError(BotBaseException):
    """Raised when moderation check fails"""
    pass


class FAQNotFoundError(BotBaseException):
    """Raised when FAQ is not found"""
    pass
