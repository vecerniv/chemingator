"""Exceptions raised by chemingator."""

from __future__ import annotations


class ChemingatorError(Exception):
    """Base class for all chemingator errors."""


class ConnectivityError(ChemingatorError):
    """An invalid or missing stream/port connection."""


class DegreesOfFreedomError(ChemingatorError):
    """A problem is over- or under-specified."""


class SolverError(ChemingatorError):
    """A solver that failed to converge."""


class BasisError(ChemingatorError):
    """Inconsistent or  unconvertible molar/mass specifications."""
