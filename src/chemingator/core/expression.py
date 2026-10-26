"""Backend-neutral types for writing residuals."""

from collections.abc import Callable
import types
from typing import Any, TypeAlias

from chemingator.core import variable

# float, sympy.Expr, ...
Scalar: TypeAlias = Any
# Maps a variable to the backend value
Resolver: TypeAlias = Callable[[variable.Variable], Scalar]
# Namespace providing operations like exp, log, ... (math, numpy, sympy, ...)
MathOps: TypeAlias = types.ModuleType
# A function producing residuals
ResidualModel: TypeAlias = Callable[[Resolver, MathOps], list[Scalar]]
# User specification equation
Constraint: TypeAlias = Callable[[Resolver, MathOps], Scalar]
