"""Exceptions for the learning and causal feedback layer."""

from __future__ import annotations

from bca2p.core import BCA2PError


class CausalGraphError(BCA2PError):
    """Raised when causal graph operations cannot be completed."""


class CounterfactualError(BCA2PError):
    """Raised when a counterfactual query is invalid or unsupported."""
