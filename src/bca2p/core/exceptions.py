"""Exception hierarchy for the bca2p core protocol layer."""

from __future__ import annotations


class BCA2PError(Exception):
    """Base exception for bca2p errors."""


class SchemaVersionError(BCA2PError):
    """Raised when serialized schema metadata does not match expectations."""


class SignalValidationError(BCA2PError):
    """Raised when signal-specific validation fails beyond schema parsing."""


class RoutingError(BCA2PError):
    """Raised when a signal cannot be routed to a valid target."""


class TrustPolicyError(BCA2PError):
    """Raised when trust or policy rules reject a routing attempt."""
