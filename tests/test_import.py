"""Smoke test: every chemingator module and public name is importable."""

import importlib

import pytest

MODULES = [
    "chemingator",
    "chemingator.core",
    "chemingator.core.component",
    "chemingator.core.expression",
    "chemingator.core.port",
    "chemingator.core.stream",
    "chemingator.core.variable",
    "chemingator.exceptions",
    "chemingator.flowsheet",
    "chemingator.properties",
    "chemingator.properties.base",
    "chemingator.units",
    "chemingator.units.base",
    "chemingator.units.mixer",
    "chemingator.units.splitter",
]

PUBLIC_NAMES = [
    "BasisError",
    "ChemingatorError",
    "Component",
    "ConnectivityError",
    "DegreesOfFreedomError",
    "Flowsheet",
    "Mixer",
    "SolverError",
    "Splitter",
    "Stream",
]


@pytest.mark.parametrize("module_name", MODULES)
def test_import_module(module_name: str) -> None:
    """Imports each module and checks the resulting module name."""
    module = importlib.import_module(module_name)
    assert module.__name__ == module_name


@pytest.mark.parametrize("name", PUBLIC_NAMES)
def test_public_name_exported(name: str) -> None:
    """Checks each public name is reachable from top-level package."""
    chemingator = importlib.import_module("chemingator")
    assert hasattr(chemingator, name)
