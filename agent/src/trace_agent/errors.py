# Copyright 2026 TRACE contributors
"""Explicit configuration and contract failure types."""

from dataclasses import dataclass
from typing import override


@dataclass(slots=True)
class ContractError(ValueError):
    """Contract failure; exception traceback fields must remain mutable."""

    detail: str

    @override
    def __str__(self) -> str:
        return self.detail


@dataclass(slots=True)
class ConfigurationError(RuntimeError):
    """Configuration failure; exception traceback fields must remain mutable."""

    variable: str

    @override
    def __str__(self) -> str:
        return f"{self.variable} must be configured before running TRACE."
