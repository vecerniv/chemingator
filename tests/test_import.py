"""Smoke test: the chemingator package is importable."""

import importlib


def test_import() -> None:
    """Imports the package and checks the resulting module name."""
    module = importlib.import_module("chemingator")
    assert module.__name__ == "chemingator"
