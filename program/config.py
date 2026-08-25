from pathlib import Path

class Config:
    """Configuration stubs — wire these up to your actual config."""

    version = "2.0"
    author = "bWlrZXNwb24="
    dept = "NOVA DC ICAC"
    updated = "2026-08-24"
    USERPROFILE = str(Path.home())  # Fallback for Windows profile path
    SQLALCHEMY_DATABASE_URI = "sqlite:///program/_VECTOR.db"
