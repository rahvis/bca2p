"""Exceptions for the stable runtime layer."""

from __future__ import annotations

from bca2p.core import BCA2PError


class RuntimeExecutionError(BCA2PError):
    """Raised when runtime execution fails irrecoverably."""


class ReplayError(BCA2PError):
    """Raised when replay or checkpoint recovery fails."""
