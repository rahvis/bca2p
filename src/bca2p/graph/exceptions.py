"""Exception types for the graph authoring layer."""

from __future__ import annotations

from bca2p.core import BCA2PError


class GraphValidationError(BCA2PError):
    """Raised when a graph cannot be compiled due to structural issues."""
