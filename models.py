#!/usr/bin/env python3

"""
models.py

Dependencies:
    pip install sqlalchemy marshmallow bcrypt
"""

import bcrypt
from contextlib import contextmanager
from datetime import datetime
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Text,
    Boolean,
    DateTime,
    LargeBinary,
    select,
)
from sqlalchemy.orm import declarative_base, sessionmaker
from marshmallow import Schema, fields


# ── Database Setup
# To add the date to the database file name
current_date = datetime.today().strftime("%Y-%m-%d")


# For SQLite databases, use the below syntax
DATABASE_URL = f"sqlite:///app_data.db"
engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(
    bind=engine,
    expire_on_commit=False,
    autoflush=False,
)

Base = declarative_base()


# ── Password Hashing
def generate_password_hash(plain_text: str) -> str:
    return bcrypt.hashpw(plain_text.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def check_password_hash(stored_hash: str, attempted: str) -> bool:
    return bcrypt.checkpw(
        attempted.encode("utf-8"),
        stored_hash.encode("utf-8")
    )


# --- MODELS ---


class Agents(Base):
    """Agents table — stores agent details."""

    __tablename__ = "agents"

    id = Column(Integer(), primary_key=True)
    agent_name = Column(String(), nullable=False, unique=True)
    agent_initials = Column(String(), nullable=False, unique=True)
    agent_parent_agency = Column(String(), nullable=False)
    agent_role = Column(String(), nullable=False)
    agent_role_secondary = Column(String())
    agent_phone = Column(String(), nullable=False, unique=True)
    agent_notes = Column(Text())

    def __repr__(self):
        return f"Agent {self.id}: {self.agent_name}"

    def __str__(self):
        return f"Agent {self.id}: {self.agent_name}"

class AgentsSchema(Schema):
    """Agent schema."""

    agent_name = fields.Str()
    agent_initials = fields.Str()
    agent_parent_agency = fields.Str()
    agent_role = fields.Str()
    agent_role_secondary = fields.Str()
    agent_phone = fields.Str()
    agent_notes = fields.Str()

agents_schema = AgentsSchema(many=True)


class Cases(Base):
    """Cases table — stores case details."""

    __tablename__ = "cases"

    id = Column(Integer(), primary_key=True)
    case_number = Column(String(), nullable=False)
    location = Column(String(), nullable=False)
    jurisdiction = Column(String(), nullable=False)
    case_date_time_begin = Column(String(), nullable=False)
    case_date_time_end = Column(String())

    def __repr__(self):
        return f"Case Number: {self.case_number}"

    def __str__(self):
        return f"Case Number: {self.case_number}"

class CaseSchema(Schema):
    """Case schema."""

    case_number = fields.Str()
    location = fields.Str()
    jurisdiction = fields.Str()
    case_date_time_begin = fields.Str()
    case_date_time_end = fields.Str()

case_schema = CaseSchema(many=True)


class Evidence(Base):
    """Evidence table — stores evidence item details."""

    __tablename__ = "evidence"

    id = Column(Integer(), primary_key=True)
    evid_num = Column(String(), nullable=False, unique=True)
    evid_qty = Column(String(), nullable=False)
    evid_desc = Column(String(), nullable=False)
    evid_model_num = Column(String(), nullable=False)
    evid_serial_num = Column(String(), nullable=False)
    evid_loc_room = Column(String(), nullable=False)
    evid_loc_room_detail = Column(String(), nullable=False)
    evid_found_by = Column(String(), nullable=False)
    evid_found_by_witness = Column(String(), nullable=False)
    evid_pic_taken = Column(String(), nullable=False)
    evid_triaged = Column(String(), nullable=False)
    evid_triaged_by = Column(String(), nullable=False)
    evid_contains_contraband = Column(String(), nullable=False)
    evid_notes = Column(Text(), nullable=False)

    def __repr__(self):
        return f"Item {self.id}: {self.evid_desc}"

    def __str__(self):
        return f"Item {self.id}: {self.evid_desc}"

class EvidenceSchema(Schema):
    """Evidence schema."""

    evid_num = fields.Str()
    evid_qty = fields.Str()
    evid_desc = fields.Str()
    evid_model_num = fields.Str()
    evid_serial_num = fields.Str()
    evid_loc_room = fields.Str()
    evid_loc_room_detail = fields.Str()
    evid_found_by = fields.Str()
    evid_found_by_witness = fields.Str()
    evid_pic_taken = fields.Str()
    evid_triaged = fields.Str()
    evid_triaged_by = fields.Str()
    evid_contains_contraband = fields.Str()
    evid_notes = fields.Str()

evid_schema = EvidenceSchema(many=True)


class Notes(Base):
    """Notes table — stores general case/agent notes."""

    __tablename__ = "notes"

    id = Column(Integer(), primary_key=True)
    note_date_time = Column(String(), nullable=False)
    note_date_time_updated = Column(String())
    note_author = Column(String(), nullable=False)
    note_text = Column(Text(), nullable=False)

    def __repr__(self):
        return f"Note {self.id}: {self.note_text}"

    def __str__(self):
        return f"Note {self.id}: {self.note_text}"

class NotesSchema(Schema):
    """Notes schema."""

    note_date_time = fields.Str()
    note_date_time_updated = fields.Str()
    note_author = fields.Str()
    note_text = fields.Str()

note_schema = NotesSchema(many=True)


class Persons(Base):
    """Persons table — stores suspect/person details."""

    __tablename__ = "persons"

    id = Column(Integer(), primary_key=True)
    sus_name = Column(String(), nullable=False, unique=True)
    sus_dob = Column(String())
    sus_address = Column(String())
    sus_phone = Column(String())
    sus_notes = Column(Text())

    def __repr__(self):
        return f"Person {self.id}: {self.sus_name}"

    def __str__(self):
        return f"Person {self.id}: {self.sus_name}"

class PersonSchema(Schema):
    """Person schema."""

    sus_name = fields.Str()
    sus_dob = fields.Str()
    sus_address = fields.Str()
    sus_phone = fields.Str()
    sus_notes = fields.Str()

person_schema = PersonSchema(many=True)


class Rooms(Base):
    """Rooms table — stores room/area details."""

    __tablename__ = "rooms"

    id = Column(Integer(), primary_key=True)
    room_label = Column(String(), nullable=False, unique=True)
    room_desc = Column(String(), nullable=False, unique=True)
    room_first_agent = Column(String(), nullable=False)
    room_second_agent = Column(String(), nullable=False)

    def __repr__(self):
        return f"Room {self.room_label}: {self.room_desc}"

    def __str__(self):
        return f"Room {self.room_label}: {self.room_desc}"


class RoomsSchema(Schema):
    """Room schema."""

    room_label = fields.Str()
    room_desc = fields.Str()
    room_first_agent = fields.Str()
    room_second_agent = fields.Str()


rooms_schema = RoomsSchema(many=True)


class UploadedFiles(Base):
    """Uploaded files table."""

    __tablename__ = "files"

    id = Column(Integer(), primary_key=True, autoincrement=True)
    file_name = Column(String(), nullable=False)
    file_size = Column(Integer(), nullable=False)
    file_mime_type = Column(String(50))
    upload_date = Column(DateTime(), default=datetime.utcnow)
    file_data = Column(LargeBinary(), nullable=False, unique=True)
    uploaded_by = Column(String(100), nullable=False)
    file_notes = Column(Text())

    def __repr__(self):
        return f"File Name: {self.file_name}, Uploaded at: {self.file_upload_date}, Notes: {self.file_notes}"

    def __str__(self):
        return f"File Name: {self.file_name}, Uploaded at: {self.file_upload_date}, Notes: {self.file_notes}"


class FileSchema(Schema):
    """File schema."""

    file_name = fields.Str()
    file_size = fields.Int()
    file_mime_type = fields.Str()
    file_notes = fields.Str()

file_schema = FileSchema(many=True)


class Users(Base):
    """Users table — authentication and user management."""

    __tablename__ = "users"

    id = Column(Integer(), primary_key=True, autoincrement=True)
    user_name = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_admin = Column(Boolean(), default=False)
    is_active = Column(Boolean(), default=False)
    created_at = Column(DateTime(), default=datetime.utcnow)

    def __repr__(self):
        return f"User Name: {self.user_name}"

    def __str__(self):
        return f"User {self.id}: {self.user_name}"

    def set_password(self, password: str):
        """Hashes a plaintext password and stores it."""
        password_bytes = password.encode("utf-8")
        salt = bcrypt.gensalt()
        self.password_hash = bcrypt.hashpw(
            password_bytes,
            salt,
        ).decode("utf-8")

    def check_password_correction(self, attempted_password: str) -> bool:
        """Checks a plaintext password against the stored bcrypt hash."""
        try:
            return bcrypt.checkpw(
                attempted_password.encode("utf-8"),
                self.password_hash.encode("utf-8"),
            )
        except (ValueError, TypeError):
            return False


# ── Table Creation ──────────────────────────────────────────
def init_db():
    """Create all tables if they don't exist."""
    Base.metadata.create_all(engine)


# ── Convenience Context Manager ─────────────────────────────
from contextlib import contextmanager

@contextmanager
def get_session():
    """Provides a transactional session scope.

    Usage:
        with get_session() as session:
            session.add(new_record)
            # commit happens automatically on exit
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
