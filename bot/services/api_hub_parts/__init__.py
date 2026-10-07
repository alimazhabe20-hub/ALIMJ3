"""Backward-compatible API Hub registry package."""
from .registry import ApiProvider, register_provider

__all__ = ["ApiProvider", "register_provider"]
