import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, relationship


def utcnow():
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


JsonType = JSON().with_variant(JSONB, "postgresql")


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
    activity_marks = relationship("ActivityMark", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship(
        "AuditLog",
        back_populates="actor",
        cascade="all, delete-orphan",
        foreign_keys="AuditLog.actor_user_id",
    )


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
    state = Column(JsonType, nullable=False)
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
    state = Column(JsonType, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    client_saved_at = Column(DateTime(timezone=True), nullable=True)

    activity_state = relationship("ActivityState", back_populates="revisions")
    user = relationship("User")


class ActivityMark(Base):
    __tablename__ = "activity_marks"
    __table_args__ = (
        UniqueConstraint("user_id", "lesson_id", "activity_id", name="uq_activity_mark"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    lesson_id = Column(String(64), nullable=False)
    activity_id = Column(String(64), nullable=False)
    status = Column(String(20), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    user = relationship("User", back_populates="activity_marks")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    target_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    action = Column(String(80), nullable=False)
    lesson_id = Column(String(64), nullable=True)
    activity_id = Column(String(64), nullable=True)
    metadata_json = Column("metadata", JsonType, nullable=True)
    ip_address = Column(String(64), nullable=True)
    user_agent = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    actor = relationship("User", foreign_keys=[actor_user_id], back_populates="audit_logs")


class LoginAttempt(Base):
    __tablename__ = "login_attempts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    identifier = Column(String(255), nullable=False, index=True)
    failed_count = Column(Integer, default=1, nullable=False)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class ApiRateLimit(Base):
    __tablename__ = "api_rate_limits"
    __table_args__ = (
        UniqueConstraint("identifier", "endpoint", name="uq_api_rate_limit"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    identifier = Column(String(255), nullable=False, index=True)  # user_id:endpoint or ip:endpoint
    endpoint = Column(String(100), nullable=False, index=True)
    request_count = Column(Integer, default=1, nullable=False)
    window_start = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)
