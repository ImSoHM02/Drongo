"""
This module defines the base models used in the achievement system.
"""

from typing import Optional, Dict, Any
from datetime import datetime
import random

class Achievement:
    """Represents an achievement with enhanced mechanics for discovery and rewards."""

    def __init__(
        self, 
        id: str, 
        name: str, 
        points: int = 10,
        hidden: bool = False,
        first_discoverer_bonus: int = 0,
        variable_requirements: Optional[Dict[str, Any]] = None,
        description: Optional[str] = None,
        hint: Optional[str] = None
    ):
        self.id = id
        self.name = name
        self.points = points
        self.hidden = hidden  # If True, achievement won't show up in lists until earned
        self.first_discoverer_bonus = first_discoverer_bonus  # Extra points for first person to get it
        self.variable_requirements = variable_requirements or {}  # Dynamic requirements that can change
        self.description = description  # Shown after earning
        self.hint = hint  # Optional cryptic hint shown before earning
        
        # Initialize any random values needed for variable requirements
        self._initialize_requirements()
    
    def _initialize_requirements(self):
        """Initialize any random values for variable requirements."""
        if self.variable_requirements:
            if 'message_count' in self.variable_requirements:
                # Randomize required message count within a range
                min_count = self.variable_requirements.get('min_count', 50)
                max_count = self.variable_requirements.get('max_count', 100)
                self.variable_requirements['current_target'] = random.randint(min_count, max_count)
            
            if 'time_window' in self.variable_requirements:
                # Randomize time window for requirements
                min_hours = self.variable_requirements.get('min_hours', 1)
                max_hours = self.variable_requirements.get('max_hours', 24)
                crosses_midnight = self.variable_requirements.get('crosses_midnight', False)
                
                if crosses_midnight:
                    # For time ranges that cross midnight (e.g., 23:00-04:00)
                    # Choose between the two ranges: evening (e.g., 23-24) or early morning (0-4)
                    if random.choice([True, False]):
                        # Evening hours
                        self.variable_requirements['current_window'] = random.randint(min_hours, 24)
                    else:
                        # Early morning hours
                        self.variable_requirements['current_window'] = random.randint(0, max_hours)
                else:
                    # Normal time range within the same day
                    self.variable_requirements['current_window'] = random.randint(min_hours, max_hours)

    def get_display_name(self, earned: bool = False) -> str:
        """Get the achievement name, considering if it's hidden and not yet earned."""
        if self.hidden and not earned:
            return "???"
        return self.name

    def get_description(self, earned: bool = False) -> str:
        """Get achievement description, considering if it's hidden and not yet earned."""
        if self.hidden and not earned:
            return self.hint if self.hint else "This achievement is a mystery..."
        return self.description if self.description else ""

    def calculate_points(self, is_first: bool = False) -> int:
        """Calculate points awarded, including first discoverer bonus if applicable."""
        return self.points + (self.first_discoverer_bonus if is_first else 0)
