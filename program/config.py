#!/usr/bin/env python3

"""
config.py

Holds basic configuration information for the app
"""

from pathlib import Path

class Config:
    """Configuration stubs."""

    version = "0.91"
    author = "SSA M. Sponheimer"
    dept = "Virginia State Police -- NOVA/DC ICAC"
    url = "github.com/LongRangeBehaviorModificationSpecialist/VECTOR_2.0"
    updated = "10-Sep-2026"
    USERPROFILE = str(Path.home())  # Fallback for Windows profile path
