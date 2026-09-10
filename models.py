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

    Z_PK = Column(Integer(), primary_key=True, autoincrement=True)
    CASENUMBER = Column(String(), nullable=False)
    LOCATION = Column(String(), nullable=False)
    JURISDICTION = Column(String(), nullable=False)
    CASEDATETIMEBEGIN = Column(String(), nullable=False)
    CASEDATETIMEEND = Column(String())

    def __repr__(self):
        return f"Case Number: {self.CASENUMBER}; Location: {self.LOCATION}"

    def __str__(self):
        return f"Case Number: {self.CASENUMBER}; Location: {self.LOCATION}"


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

    Z_PK = Column(Integer(), primary_key=True, autoincrement=True)
    AGENTNAME = Column(String(), nullable=False, unique=True)
    AGENTPARENTAGENCY = Column(String(), nullable=False)
    AGENTPRIMARYROLE = Column(String(), nullable=False)
    AGENTROLESECONDARY = Column(String())
    AGENTPHONE = Column(String(), nullable=False, unique=True)
    AGENTEMAIL = Column(String(), unique=True)
    AGENTNOTE = Column(Text())
    ENTEREDDATETIME = Column(String())

    def __repr__(self):
        return f"Agent ID: {self.Z_PK}: Name: {self.AGENTNAME}"

    def __str__(self):
        return f"Agent ID: {self.Z_PK}; Name: {self.AGENTNAME}"


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

    Z_PK = Column(Integer(), primary_key=True, autoincrement=True)
    ROOMLABEL = Column(String(), nullable=False, unique=True)
    ROOMDESC = Column(String(), nullable=False, unique=True)
    ROOMFIRSTAGENT = Column(String(), nullable=False)
    ROOMSECONDAGENT = Column(String(), nullable=False)
    ROOMNOTE = Column(Text())
    ENTEREDDATETIME = Column(String())

    def __repr__(self):
        return f"Room {self.ROOMLABEL} ({self.ROOMDESC})"

    def __str__(self):
        return f"Room {self.ROOMLABEL} ({self.ROOMDESC})"


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

    Z_PK = Column(Integer(), primary_key=True, autoincrement=True)
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

    Z_PK = Column(Integer(), primary_key=True, autoincrement=True)
    PERSONNAME = Column(String(), nullable=False, unique=True)
    PERSONDOB = Column(String())
    PERSONADDRESS = Column(String())
    PERSONPHONE = Column(String())
    SUSPECTNOTE = Column(Text())
    ENTEREDDATETIME = Column(String())

    def __repr__(self):
        return f"Person {self.Z_PK}: {self.PERSONNAME}"

    def __str__(self):
        return f"Person {self.Z_PK}: {self.PERSONNAME}"


class PersonSchema(Schema):
    """Person schema."""

    PERSONNAME = fields.Str()
    PERSONDOB = fields.Str()
    PERSONADDRESS = fields.Str()
    PERSONPHONE = fields.Str()
    SUSPECTNOTE = fields.Str()
    ENTEREDDATETIME = fields.Str()


person_schema = PersonSchema(many=True)


class Notes(Base):
    """Notes table — stores general case/agent notes."""

    __tablename__ = "NOTES"

    Z_PK = Column(Integer(), primary_key=True, autoincrement=True)
    NOTEDATETIME = Column(String(), nullable=False)
    NOTEDATETIMEUPDATED = Column(String())
    NOTEAUTHOR = Column(String(), nullable=False)
    NOTETEXT = Column(Text(), nullable=False)

    def __repr__(self):
        return f"Note {self.Z_PK}: {self.NOTETEXT}"

    def __str__(self):
        return f"Note {self.Z_PK}: {self.NOTETEXT}"

class NotesSchema(Schema):
    """Notes schema."""

    NOTEDATETIME = fields.Str()
    NOTEDATETIMEUPDATED = fields.Str()
    NOTEAUTHOR = fields.Str()
    NOTETEXT = fields.Str()

note_schema = NotesSchema(many=True)


class UploadedFiles(Base):
    """Uploaded files table."""

    __tablename__ = "FILES"

    Z_PK = Column(Integer(), primary_key=True, autoincrement=True)
    FILENAME = Column(String(), nullable=False)
    FILESIZE = Column(Integer(), nullable=False)
    FILEMIMETYPE = Column(String(50))
    FILEUPLOADDATE = Column(DateTime(), default=datetime.utcnow)
    FILEUPLOADEDBY = Column(String(100), nullable=False)
    FILEDATA = Column(LargeBinary(), nullable=False, unique=True)
    FILENOTE = Column(String())

    def __repr__(self):
        return f"File: {self.FILENAME}, Uploaded at: {self.FILEUPLOADDATE}"

    def __str__(self):
        return f"File: {self.FILENAME}, Uploaded at: {self.FILEUPLOADDATE}"


class FileSchema(Schema):
    """File schema."""

    FILENAME = fields.Str()
    FILESIZE = fields.Int()
    FILEMIMETYPE = fields.Str()
    FILEUPLOADDATE = fields.Str()
    FILEUPLOADEDBY = fields.Str()
    FILENOTE = fields.Str()

file_schema = FileSchema(many=True)


class Users(UsersBase):
    """Users table — authentication and user management."""

    __tablename__ = "users"

    Z_PK = Column(Integer(), primary_key=True, autoincrement=True)
    USERNAME = Column(String(100), unique=True, nullable=False)
    PASSWORDHASH = Column(String(255), nullable=False)
    ISADMIN = Column(Boolean(), default=False)
    ISACTIVE = Column(Boolean(), default=True)
    MUSTCHANGEPASSWORD = Column(Boolean, default=True)
    ENTEREDDATETIME = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"User Name: {self.USERNAME}"

    def __str__(self):
        return f"User {self.Z_PK}: {self.USERNAME}"

    def set_password(self, password: str):
        """Hashes a plaintext password and stores hash value."""
        password_bytes = password.encode("utf-8")
        salt = bcrypt.gensalt()
        self.PASSWORDHASH = bcrypt.hashpw(
            password_bytes, salt
        ).decode("utf-8")

    def check_password_correction(self, attempted_password: str) -> bool:
        """Checks a plaintext password against the stored bcrypt hash."""
        try:
            return bcrypt.checkpw(
                attempted_password.encode("utf-8"),
                self.PASSWORDHASH.encode("utf-8"),
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
