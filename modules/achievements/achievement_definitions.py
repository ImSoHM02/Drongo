"""
This module defines the achievements available in the system.

Each achievement is represented by an Achievement object with enhanced mechanics for discovery and rewards.
"""

from modules.achievements.models import Achievement

achievements = {
    "MARATHON_SPEAKER": Achievement(
        "MARATHON_SPEAKER",
        "Marathon Speaker",
        points=30,
        description="Spent a long time in voice chat with others",
        hidden=True,
        hint="That's quite the mouth...",
        variable_requirements={
            'time_window': True,
            'min_hours': 1,
            'max_hours': 3
        }
    ),
    
    "SOCIAL_BUTTERFLY": Achievement(
        "SOCIAL_BUTTERFLY",
        "Social Butterfly",
        points=20,
        description="Connected with multiple different people in voice chat",
        hidden=True,
        hint="Being social with others can be a great thing...",
        first_discoverer_bonus=10  # Extra points for first to achieve
    ),
    
    "CHATTY": Achievement(
        "CHATTY",
        "Message Master",
        points=15,
        description="Sent many messages in a short time",
        hidden=True,
        hint="Perhaps typing will get you there?...",
        variable_requirements={
            'message_count': True,
            'min_count': 80,
            'max_count': 120
        }
    ),
    
    "SUPER_CHATTY": Achievement(
        "SUPER_CHATTY",
        "Communication King",
        points=30,
        description="Demonstrated exceptional messaging activity",
        hidden=True,
        hint="Those are quite the fingers you have there...",
        variable_requirements={
            'message_count': True,
            'min_count': 200,
            'max_count': 300
        }
    ),
    
    "NIGHT_OWL": Achievement(
        "NIGHT_OWL",
        "Night Owl",
        points=20,
        description="Active during the quiet hours",
        hidden=True,
        hint="Some achievements are best earned when others are sleeping...",
        variable_requirements={
            'time_window': True,
            'min_hours': 22,  # 10 PM
            'max_hours': 4,   # 4 AM
            'crosses_midnight': True  # Indicates this time range crosses midnight
        }
    ),
    
    "PATTERN_MASTER": Achievement(
        "PATTERN_MASTER",
        "Pattern Master",
        points=25,
        hidden=True,
        description="Found a hidden message pattern",
        hint="Sometimes messages follow a special pattern...",
        first_discoverer_bonus=15
    ),
    
    "REACTION_CHAIN": Achievement(
        "REACTION_CHAIN",
        "Chain Reactor",
        points=20,
        description="Part of a reaction chain",
        variable_requirements={
            'min_chain': 5,
            'max_chain': 8
        }
    ),
    
    "ALPHABET_SOUP": Achievement(
        "ALPHABET_SOUP",
        "Alphabet Soup",
        points=25,
        description="Used every letter of the alphabet in a message",
        first_discoverer_bonus=1
    ),
    
    "LUCKY_NUMBER": Achievement(
        "LUCKY_NUMBER",
        "Lucky Number",
        points=15,
        hidden=True,
        hint="Some numbers are luckier than others...",
        description="Found the lucky number of the day",
        variable_requirements={
            'number_range': True,
            'min_number': 1,
            'max_number': 1000
        }
    ),
    
    "COMBO_BREAKER": Achievement(
        "COMBO_BREAKER",
        "Combo Breaker",
        points=20,
        description="Achieved something special in rapid succession",
        variable_requirements={
            'combo_time': True,
            'min_seconds': 10,
            'max_seconds': 30
        }
    ),
    
    "TREASURE_HUNTER": Achievement(
        "TREASURE_HUNTER",
        "Treasure Hunter",
        points=30,
        hidden=True,
        hint="There are hidden treasures in everyday conversations...",
        description="Found a rare hidden message combination",
        first_discoverer_bonus=20
    ),
    
    "TIME_TRAVELER": Achievement(
        "TIME_TRAVELER",
        "Time Traveler",
        points=25,
        hidden=True,
        hint="Sometimes the past comes back to visit...",
        description="Interacted with a message from long ago",
        first_discoverer_bonus=10
    )
}
