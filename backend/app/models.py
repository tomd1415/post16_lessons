import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, relationship


def utcnow():
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class UserRole(str, enum.Enum):
    pupil = "pupil"
    teacher = "teacher"
    admin = "admin"


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(64), unique=True, index=True, nullable=False)
    name = Column(String(120), nullable=False)
    role = Column(String(20), nullable=False, default=UserRole.pupil.value)
    cohort_year = Column(String(20), nullable=True)
    teacher_notes = Column(Text, nullable=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    failed_login_count = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    active = Column(Boolean, default=True, nullable=False)

    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    activity_states = relationship("ActivityState", back_populates="user", cascade="all, delete-orphan")


class Session(Base):
    __tablename__ = "sessions"

    id = Column(String(64), primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    csrf_token = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    ip_address = Column(String(64), nullable=True)
    user_agent = Column(String(255), nullable=True)

    user = relationship("User", back_populates="sessions")


class ActivityState(Base):
    __tablename__ = "activity_states"
    __table_args__ = (
        UniqueConstraint("user_id", "lesson_id", "activity_id", name="uq_activity_state"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    lesson_id = Column(String(64), nullable=False)
    activity_id = Column(String(64), nullable=False)
    state = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)
    last_client_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="activity_states")
    revisions = relationship("ActivityRevision", back_populates="activity_state", cascade="all, delete-orphan")


class ActivityRevision(Base):
    __tablename__ = "activity_revisions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    activity_state_id = Column(UUID(as_uuid=True), ForeignKey("activity_states.id"), nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    lesson_id = Column(String(64), nullable=False)
    activity_id = Column(String(64), nullable=False)
    state = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    client_saved_at = Column(DateTime(timezone=True), nullable=True)

    activity_state = relationship("ActivityState", back_populates="revisions")
    user = relationship("User")
