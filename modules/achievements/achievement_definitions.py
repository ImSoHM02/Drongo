"""
This module defines the achievements available in the system.

Each achievement is represented by an Achievement object, which has the following attributes:
    id: A unique identifier for the achievement.
    name: The name of the achievement.
    description: A description of the achievement.
    points: The number of points awarded for earning the achievement.
"""

from modules.achievements.models import Achievement

achievements = {
    "FIRST_REQUEST": Achievement(
        "FIRST_REQUEST",
        "Test Achievement",
        "Earned by asking for an achievement using the 'iwantanachievement' secret word",
        points=5
    ),
    "CHATTY": Achievement(
        "CHATTY",
        "Talks-a-lot",
        "Sent 50 messages in a single day",
        points=15
    ),
    "SUPER_CHATTY": Achievement(
        "SUPER_CHATTY",
        "Talks-too-much",
        "Sent 100 messages in a single day",
        points=30
    ),
    "LOVE_HOMIES": Achievement(
        "LOVE_HOMIES",
        "Showing some love to the homies <3",
        "We love our homies",
        points=10
    ),
    "BUMBAG": Achievement(
        "BUMBAG",
        "Bumbag",
        "You adjusted your bumbag in public",
        points=10
    ),
    "BIG_PUFF": Achievement(
        "BIG_PUFF",
        "Big Puff",
        "Took a big puff of your ciggie",
        points=10
    ),
    "TN_ROLL": Achievement(
        "TN_ROLL",
        "Rolled your first pair of TN's",
        "Rolled a fuckin' nerd for his TN's",
        points=10
    ),
    "NOT_A_PROGRAMMER": Achievement(
        "NOT_A_PROGRAMMER",
        "Not a programmer",
        "Probably sarcastically told Sean he's not a programmer",
        points=30
    ),
    "TRUE_AUSSIE": Achievement(
        "TRUE_AUSSIE",
        "True Aussie",
        "Used some true Aussie insults",
        points=10
    ),
    "BROKE_LEG": Achievement(
        "BROKE_LEG",
        "MY LEG!",
        "Probably talking about how Jamie broke his leg",
        points=10
    ),
    "CURSED": Achievement(
        "CURSED",
        "Cursed",
        "Used the best emoji of all time",
        points=20
    )
}
