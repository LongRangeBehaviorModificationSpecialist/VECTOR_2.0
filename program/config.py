from pathlib import Path

class Config:
    """Configuration stubs — wire these up to your actual config."""

    version = "0.91"
    author = "SSA M. Sponheimer"
    dept = "Virginia State Police -- NOVA/DC ICAC"
    url = "https://github.com/LongRangeBehaviorModificationSpecialist/VECTOR_2.0"
    updated = "31-Aug-2026"
    USERPROFILE = str(Path.home())  # Fallback for Windows profile path
