
# Message handling constants
MAX_MESSAGE_LENGTH = 1900  # Leave room for Discord's overhead
MAX_HISTORY_LENGTH = 30

# File type constants
TEXT_FILE_EXTENSIONS = ('.txt', '.py', '.js', '.html', '.css', '.json', '.xml', '.md')

# Model constants
DEFAULT_MODEL = "claude-3-7-sonnet-20250219"
DEFAULT_MAX_TOKENS = 8192
DEFAULT_TEMPERATURE = 0.8
BRIEF_MAX_TOKENS = 150
BRIEF_TEMPERATURE = 0.9

EXTENDED_THINKING_BUDGET = 4096 # Default token budget when extended thinking is enabled
EXTENDED_OUTPUT_MAX_TOKENS = 128000 # Max tokens when using 128k output beta
EXTENDED_OUTPUT_BETA_FLAG = "output-128k-2025-02-19" # Beta flag value for 128k output
# Probability configurations
DEFAULT_CONFIG = {
    "name": "default",
    "total_chance": 0.002,
    "insult_weight": 0.5,
    "compliment_weight": 0.5
}

FRIENDLY_CONFIG = {
    "name": "friendly",
    "total_chance": 0.01,
    "insult_weight": 0,
    "compliment_weight": 1
}

NOT_FRIENDLY_CONFIG = {
    "name": "not-friendly",
    "total_chance": 0.01,
    "insult_weight": 1,
    "compliment_weight": 0
}

# Test configurations for image feature
TEST_INSULTS_CONFIG = {
    "name": "test-insults",
    "total_chance": 1.0,  # 100% chance to respond
    "insult_weight": 1,   # 100% insults
    "compliment_weight": 0
}

TEST_COMPLIMENTS_CONFIG = {
    "name": "test-compliments",
    "total_chance": 1.0,  # 100% chance to respond
    "insult_weight": 0,
    "compliment_weight": 1  # 100% compliments
}

# Error messages
ERROR_MESSAGES = {
    "download_failed": "Sorry, I couldn't download the attachment.",
    "decode_failed": "Sorry, I can only read text-based files.",
    "general_error": "Sorry, mate. I'm having a bit of a technical hiccup. Give me a sec to sort myself out.",
    "mode_error": "Oi that mode don't exist ya drongo!",
    "unauthorized": "Oi nah, you ain't got the juice to be messin' with my settings, ya drongo!",
    "mode_change_error": "Oi somethin's fucked with the mode change: {error}"
}
