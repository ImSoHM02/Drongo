"""
This module defines the achievements available in the system.

Each achievement is represented by an Achievement object, which has the following attributes:
    id: A unique identifier for the achievement.
    name: The name of the achievement.
    points: The number of points awarded for earning the achievement.
"""

from modules.achievements.models import Achievement

achievements = {
    "MARATHON_SPEAKER": Achievement(
        "MARATHON_SPEAKER",
        "Marathon Speaker",
        points=30
    ),
    "SOCIAL_BUTTERFLY": Achievement(
        "SOCIAL_BUTTERFLY",
        "Social Butterfly",
        points=20
    ),
    "FIRST_REQUEST": Achievement(
        "FIRST_REQUEST",
        "Test Achievement",
        points=5
    ),
    "CHATTY": Achievement(
        "CHATTY",
        "Talks-a-lot",
        points=15
    ),
    "SUPER_CHATTY": Achievement(
        "SUPER_CHATTY",
        "Talks-too-much",
        points=30
    ),
    "LOVE_HOMIES": Achievement(
        "LOVE_HOMIES",
        "Showing some love to the homies <3",
        points=10
    ),
    "BUMBAG": Achievement(
        "BUMBAG",
        "Bumbag",
        points=10
    ),
    "BIG_PUFF": Achievement(
        "BIG_PUFF",
        "Big Puff",
        points=10
    ),
    "TN_ROLL": Achievement(
        "TN_ROLL",
        "Rolled your first pair of TN's",
        points=10
    ),
    "NOT_A_PROGRAMMER": Achievement(
        "NOT_A_PROGRAMMER",
        "Not a programmer",
        points=30
    ),
    "TRUE_AUSSIE": Achievement(
        "TRUE_AUSSIE",
        "True Aussie",
        points=10
    ),
    "BROKE_LEG": Achievement(
        "BROKE_LEG",
        "MY LEG!",
        points=10
    ),
    "CURSED": Achievement(
        "CURSED",
        "Cursed",
        points=20
    ),
    "ALPHABET_SOUP": Achievement(
        "ALPHABET_SOUP",
        "Alphabet Soup",
        points=25
    )
}
