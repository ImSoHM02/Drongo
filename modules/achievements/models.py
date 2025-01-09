"""
This module defines the base models used in the achievement system.
"""

class Achievement:
    """Represents an achievement with an ID, name, and points."""

    def __init__(self, id: str, name: str, points: int = 10):
        self.id = id
        self.name = name
        self.points = points
