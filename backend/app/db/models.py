from datetime import date, datetime
from enum import Enum

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
    func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class RecurrenceFreq(str, Enum):
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"



note_tags = Table(
    "note_tags",
    Base.metadata,
    Column(
        "note_id",
        Integer,
        ForeignKey("notes.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "tag_id",
        Integer,
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)



class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
    )

    username: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    timezone: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="UTC",
        server_default="UTC",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default="now()",
    )

    notes: Mapped[list["Note"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    tags: Mapped[list["Tag"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )



class Note(Base):
    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    body: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    starts_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )

    recurrence_freq: Mapped[RecurrenceFreq | None] = mapped_column(
        SqlEnum(
            RecurrenceFreq,
            name="recurrence_freq",
        ),
        nullable=True,
    )

    recurrence_until: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default="now()",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )

    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )


    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    user: Mapped["User"] = relationship(
        back_populates="notes",
    )

    exceptions: Mapped[list["NoteException"]] = relationship(
        back_populates="note",
        cascade="all, delete-orphan",
    )

    tags: Mapped[list["Tag"]] = relationship(
        secondary=note_tags,
        back_populates="notes",
    )

    reminders: Mapped[list["Reminder"]] = relationship(
        back_populates="note",
        cascade="all, delete-orphan",
    )

    __mapper_args__ = {
        "version_id_col": version,
        "eager_defaults": True,
    }
    
    __table_args__ = (
        Index(
            "ix_notes_user_id_starts_at",
            "user_id",
            "starts_at",
        ),
        Index(
            "ix_notes_user_id_deleted_at",
            "user_id",
            "deleted_at",
        ),
        Index(
            "ix_notes_user_id_updated_at",
            "user_id",
            "updated_at",
        ),
    )



class NoteException(Base):
    __tablename__ = "note_exceptions"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    note_id: Mapped[int] = mapped_column(
        ForeignKey("notes.id", ondelete="CASCADE"),
        nullable=False,
    )

    original_starts_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    title: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    body: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    starts_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    note: Mapped["Note"] = relationship(
        back_populates="exceptions",
    )

    __table_args__ = (
        UniqueConstraint(
            "note_id",
            "original_starts_at",
            name="uq_note_exceptions_note_original_start",
        ),
    )



class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    color: Mapped[str] = mapped_column(
        String(7),
        nullable=False,
        default="#888888",
        server_default="#888888",
    )

    user: Mapped["User"] = relationship(
        back_populates="tags",
    )

    notes: Mapped[list["Note"]] = relationship(
        secondary=note_tags,
        back_populates="tags",
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "name",
            name="uq_tags_user_name",
        ),
    )



class Reminder(Base):
    __tablename__ = "reminders"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    note_id: Mapped[int] = mapped_column(
        ForeignKey("notes.id", ondelete="CASCADE"),
        nullable=False,
    )

    offset_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    note: Mapped["Note"] = relationship(
        back_populates="reminders",
    )

    deliveries: Mapped[list["ReminderDelivery"]] = relationship(
        back_populates="reminder",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint(
            "note_id",
            "offset_minutes",
            name="uq_reminders_note_offset",
        ),
    )



class ReminderDelivery(Base):
    __tablename__ = "reminder_deliveries"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    reminder_id: Mapped[int] = mapped_column(
        ForeignKey("reminders.id", ondelete="CASCADE"),
        nullable=False,
    )

    occurrence_starts_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default="now()",
    )

    reminder: Mapped["Reminder"] = relationship(
        back_populates="deliveries",
    )

    __table_args__ = (
        UniqueConstraint(
            "reminder_id",
            "occurrence_starts_at",
            name="uq_reminder_deliveries_occurrence",
        ),
    )