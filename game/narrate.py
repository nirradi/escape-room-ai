"""Narration data model.

Provides a consistent interface for narration output.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Narration:
    """Represents a narration output."""
    text: str
