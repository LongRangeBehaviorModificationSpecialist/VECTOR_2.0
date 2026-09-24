"""Every module imports.

Splitting a long page builder into a new module puts code in a file that
nothing imports until VECTOR starts. The suite ran green once with
parts/admin_users.py holding an indentation error, because no test
touched it -- the application would have failed on the first start
instead. So: import every module, and let a broken one fail here.

main.py is left out on purpose. Importing it starts the application.
"""

import importlib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

SKIP = {"main", "conftest"}


def _module_names() -> list:
    names = [
        path.stem
        for path in sorted(ROOT.glob("*.py"))
        if path.stem not in SKIP
    ]
    for package in ("parts", "program", "tools"):
        for path in sorted((ROOT / package).glob("*.py")):
            if path.stem == "__init__":
                continue
            names.append(
                f"{package}.{path.stem}" if package != "tools" else path.stem
            )
    return names


MODULES = _module_names()


def test_there_are_modules_to_check():
    """A glob that matches nothing would pass every test below."""
    assert len(MODULES) > 20, MODULES


@pytest.mark.parametrize("name", MODULES)
def test_the_module_imports(name):
    if name in ("encrypt_database", "decrypt_database", "make_demo_case"):
        # tools/ is on its own path when run as a script.
        import sys
        sys.path.insert(0, str(ROOT / "tools"))
    importlib.import_module(name)
