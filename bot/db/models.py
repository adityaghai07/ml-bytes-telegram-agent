"""
Database Models using SQLAlchemy ORM

Each class represents a database table.
"""

from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Boolean,
    ForeignKey,
    Float,
    BigInteger,
)
from sqlalchemy.orm import relationship, DeclarativeBase
from sqlalchemy.dialects.postgresql import ARRAY


class Base(DeclarativeBase):
    """Base class for all ORM models"""
    pass


class User(Base):
    """Community members (students, mentors, admins)"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)

    is_admin = Column(Boolean, default=False)
    is_mentor = Column(Boolean, default=False)
    expertise_domains = Column(ARRAY(String), default=list)

    joined_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    messages = relationship("Message", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.username} ({self.telegram_id})>"


class Message(Base):
    """Messages sent in the community"""
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    text = Column(Text, nullable=False)
    telegram_message_id = Column(BigInteger, nullable=False)

    is_deleted = Column(Boolean, default=False)
    deletion_reason = Column(String(255), nullable=True)
    sent_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="messages")
    mentor_tags = relationship("MentorTag", back_populates="message", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Message {self.id} from User {self.user_id}>"


class FAQ(Base):
    """Frequently asked questions with embeddings for similarity search"""
    __tablename__ = "faqs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    category = Column(String(100), nullable=True)
    embedding = Column(ARRAY(Float), nullable=True)

    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    times_matched = Column(Integer, default=0)

    def __repr__(self):
        return f"<FAQ {self.id}: {self.question[:50]}...>"


class MentorTag(Base):
    """Tracks mentor tags on messages"""
    __tablename__ = "mentor_tags"

    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=False)
    mentor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    reason = Column(String(255), nullable=True)
    tagged_at = Column(DateTime, default=datetime.utcnow)

    responded = Column(Boolean, default=False)
    responded_at = Column(DateTime, nullable=True)

    message = relationship("Message", back_populates="mentor_tags")
    mentor = relationship("User")

    def __repr__(self):
        return f"<MentorTag: Mentor {self.mentor_id} tagged for Message {self.message_id}>"


class ModerationLog(Base):
    """Audit log for moderation actions"""
    __tablename__ = "moderation_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    action = Column(String(50), nullable=False)
    reason = Column(String(255), nullable=False)
    confidence = Column(Float, nullable=False)
    message_text = Column(Text, nullable=True)

    moderated_at = Column(DateTime, default=datetime.utcnow)
    llm_provider = Column(String(50), nullable=True)

    def __repr__(self):
        return f"<ModerationLog: {self.action} on Message {self.message_id}>"
