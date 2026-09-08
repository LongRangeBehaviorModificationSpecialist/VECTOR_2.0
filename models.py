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
)
from sqlalchemy.orm import declarative_base, sessionmaker
from marshmallow import Schema, fields


# ----- Database Setup -----
# To add the date to the database file name
current_date = datetime.today().strftime("%Y-%m-%d")


# ----- Main database -----
DATABASE_URL = f"sqlite:///db/app_data.db"

engine = create_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    connect_args={"check_same_thread": False}
)

Session = sessionmaker(bind=engine)

# ----- Users database -----
USERS_DATABASE_URL = "sqlite:///db/users.db"

users_engine = create_engine(
    USERS_DATABASE_URL,
    connect_args={"check_same_thread": False}
)

UsersSession = sessionmaker(bind=users_engine)


# Main modles -> app_data.db
Base = declarative_base()

# Users model -> users.db
UsersBase = declarative_base()

# ----- MODELS -----


class Cases(Base):
    """Cases table — stores case details."""

    __tablename__ = "CASES"

    Z_PK = Column(Integer(), primary_key=True)
    CASENUMBER = Column(String(), nullable=False)
    LOCATION = Column(String(), nullable=False)
    JURISDICTION = Column(String(), nullable=False)
    CASEDATETIMEBEGIN = Column(String(), nullable=False)
    CASEDATETIMEEND = Column(String())

    def __repr__(self):
        return f"Case Number: {self.CASENUMBER}"

    def __str__(self):
        return f"Case Number: {self.CASENUMBER}"


class CaseSchema(Schema):
    """Case schema."""

    CASENUMBER = fields.Str()
    LOCATION = fields.Str()
    JURISDICTION = fields.Str()
    CASEDATETIMEBEGIN = fields.Str()
    CASEDATETIMEEND = fields.Str()


case_schema = CaseSchema(many=True)


class Agents(Base):
    """Agents table — stores agent details."""

    __tablename__ = "AGENTS"

    Z_PK = Column(Integer(), primary_key=True)
    AGENTNAME = Column(String(), nullable=False, unique=True)
    AGENTPARENTAGENCY = Column(String(), nullable=False)
    AGENTPRIMARYROLE = Column(String(), nullable=False)
    AGENTROLESECONDARY = Column(String())
    AGENTPHONE = Column(String(), nullable=False, unique=True)
    AGENTEMAIL = Column(String(), unique=True)
    AGENTNOTE = Column(Text())
    ENTEREDDATETIME = Column(String())

    def __repr__(self):
        return f"Agent {self.Z_PK}: {self.AGENTNAME}"

    def __str__(self):
        return f"Agent {self.Z_PK}: {self.AGENTNAME}"


class AgentsSchema(Schema):
    """Agent schema."""

    AGENTNAME = fields.Str()
    AGENTPARENTAGENCY = fields.Str()
    AGENTPRIMARYROLE = fields.Str()
    AGENTROLESECONDARY = fields.Str()
    AGENTPHONE = fields.Str()
    AGENTEMAIL = fields.Str()
    AGENTNOTE = fields.Str()
    ENTEREDDATETIME = fields.Str()

agents_schema = AgentsSchema(many=True)


class Rooms(Base):
    """Rooms table — stores room/area details."""

    __tablename__ = "ROOMS"

    Z_PK = Column(Integer(), primary_key=True)
    ROOMLABEL = Column(String(), nullable=False, unique=True)
    ROOMDESC = Column(String(), nullable=False, unique=True)
    ROOMFIRSTAGENT = Column(String(), nullable=False)
    ROOMSECONDAGENT = Column(String(), nullable=False)
    ROOMNOTE = Column(Text())
    ENTEREDDATETIME = Column(String())

    def __repr__(self):
        return f"Room {self.ROOMLABEL}: {self.ROOMDESC}"

    def __str__(self):
        return f"Room {self.ROOMLABEL}: {self.ROOMDESC}"


class RoomsSchema(Schema):
    """Room schema."""

    ROOMLABEL = fields.Str()
    ROOMDESC = fields.Str()
    ROOMFIRSTAGENT = fields.Str()
    ROOMSECONDAGENT = fields.Str()
    ROOMNOTE = fields.Str()
    ENTEREDDATETIME = fields.Str()


rooms_schema = RoomsSchema(many=True)


class Evidence(Base):
    """Evidence table — stores evidence item details."""

    __tablename__ = "EVIDENCE"

    Z_PK = Column(Integer(), primary_key=True)
    EVIDNUM = Column(String(), nullable=False, unique=True)
    EVIDQTY = Column(String(), nullable=False)
    EVIDDESC = Column(String(), nullable=False)
    EVIDMODELNUMBER = Column(String())
    EVIDSERIALNUMBER = Column(String())
    EVIDLOCROOM = Column(String(), nullable=False)
    EVIDLOCROOMDETAIL = Column(String(), nullable=False)
    EVIDFOUNDBY = Column(String(), nullable=False)
    EVIDFOUNDBYWITNESS = Column(String(), nullable=False)
    EVIDPICTAKEN = Column(String())
    EVIDTRIAGED = Column(String())
    EVIDTRIAGEDBY = Column(String())
    EVIDISCONTRABAND = Column(String())
    EVIDNOTE = Column(Text())
    ENTEREDDATETIME = Column(String())

    def __repr__(self):
        return f"Item {self.Z_PK}: {self.EVIDDESC}"

    def __str__(self):
        return f"Item {self.Z_PK}: {self.EVIDDESC}"

class EvidenceSchema(Schema):
    """Evidence schema."""

    EVIDNUM = fields.Str()
    EVIDQTY = fields.Str()
    EVIDDESC = fields.Str()
    EVIDMODELNUMBER = fields.Str()
    EVIDSERIALNUMBER = fields.Str()
    EVIDLOCROOM = fields.Str()
    EVIDLOCROOMDETAIL = fields.Str()
    EVIDFOUNDBY = fields.Str()
    EVIDFOUNDBYWITNESS = fields.Str()
    EVIDPICTAKEN = fields.Str()
    EVIDTRIAGED = fields.Str()
    EVIDTRIAGEDBY = fields.Str()
    EVIDISCONTRABAND = fields.Str()
    EVIDNOTE = fields.Str()
    ENTEREDDATETIME = fields.Str()

evid_schema = EvidenceSchema(many=True)


class Persons(Base):
    """Persons table — stores suspect/person details."""

    __tablename__ = "PERSONS"

    Z_PK = Column(Integer(), primary_key=True)
    SUSPECTNAME = Column(String(), nullable=False, unique=True)
    SUSPECTDOB = Column(String())
    SUSPECTADDRESS = Column(String())
    SUSPECTPHONE = Column(String())
    SUSPECTNOTE = Column(Text())
    ENTEREDDATETIME = Column(String())

    def __repr__(self):
        return f"Person {self.Z_PK}: {self.SUSPECTNAME}"

    def __str__(self):
        return f"Person {self.Z_PK}: {self.SUSPECTNAME}"


class PersonSchema(Schema):
    """Person schema."""

    SUSPECTNAME = fields.Str()
    SUSPECTDOB = fields.Str()
    SUSPECTADDRESS = fields.Str()
    SUSPECTPHONE = fields.Str()
    SUSPECTNOTE = fields.Str()
    ENTEREDDATETIME = fields.Str()


person_schema = PersonSchema(many=True)


class Notes(Base):
    """Notes table — stores general case/agent notes."""

    __tablename__ = "NOTES"

    Z_PK = Column(Integer(), primary_key=True)
    NOTEDATETIME = Column(String(), nullable=False)
    NOTEDATETIMEUPDATED = Column(String())
    NOTEAUTHOR = Column(String(), nullable=False)
    NOTETEXT = Column(Text(), nullable=False)

    def __repr__(self):
        return f"Note {self.Z_PK}: {self.note_text}"

    def __str__(self):
        return f"Note {self.Z_PK}: {self.note_text}"

class NotesSchema(Schema):
    """Notes schema."""

    NOTEDATETIME = fields.Str()
    NOTEDATETIMEUPDATED = fields.Str()
    NOTEAUTHOR = fields.Str()
    NOTETEXT = fields.Str()

note_schema = NotesSchema(many=True)


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

    def __repr__(self):
        return f"File Name: {self.file_name}, Uploaded at: {self.upload_date}"

    def __str__(self):
        return f"File Name: {self.file_name}, Uploaded at: {self.upload_date}"


class FileSchema(Schema):
    """File schema."""

    file_name = fields.Str()
    file_size = fields.Int()
    file_mime_type = fields.Str()
    file_note = fields.Str()
    upload_date = fields.Str()
    uploaded_by = fields.Str()

file_schema = FileSchema(many=True)


class Users(UsersBase):
    """Users table — authentication and user management."""

    __tablename__ = "users"

    id = Column(Integer(), primary_key=True, autoincrement=True)
    user_name = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_admin = Column(Boolean(), default=False)
    is_active = Column(Boolean(), default=True)
    must_change_password = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"User Name: {self.user_name}"

    def __str__(self):
        return f"User {self.id}: {self.user_name}"

    def set_password(self, password: str):
        """Hashes a plaintext password and stores it."""
        password_bytes = password.encode("utf-8")
        salt = bcrypt.gensalt()
        self.password_hash = bcrypt.hashpw(
            password_bytes, salt
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


DEFAULT_USER_PASSWORD = "Vector2026!"


# ----- Table Creation -----
def init_db():
    """Initialize both databases."""
    Base.metadata.create_all(engine)

    # Create ONLY the Users table in users.db
    UsersBase.metadata.create_all(users_engine)


# ----- Convenience Context Manager -----
from contextlib import contextmanager

@contextmanager
def get_session():
    """Provides a transactional session scope.

    Usage:
        with get_session() as session:
            session.add(new_record)
            # commit happens automatically on exit
    """
    session = Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@contextmanager
def get_users_session():
    """Provides a transactional session scope for the users database.

    Usage:
        with get_users_session() as session:
            session.add(new_user)
            # commit happens automatically on exit
    """
    session = UsersSession()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
