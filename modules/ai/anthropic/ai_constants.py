
# Message handling constants
MAX_MESSAGE_LENGTH = 1900  # Leave room for Discord's overhead
MAX_HISTORY_LENGTH = 30

# Trigger constants
TRIGGER_PHRASE = "oi drongo"
TRIGGER_PATTERN = r'^oi\s+drongo\s*'

# Role constants
ROLE_USER = "user"
ROLE_ASSISTANT = "assistant"
ROLE_HUMAN = "human"  # Legacy role name, converted to ROLE_USER

# API content block types
CONTENT_TYPE_TEXT = "text"
CONTENT_TYPE_IMAGE = "image"

# API tool constants
TOOL_TYPE_WEB_SEARCH = "web_search_20250305"
TOOL_NAME_WEB_SEARCH = "web_search"

# Image processing constants
IMAGE_SOURCE_TYPE = "base64"
DEFAULT_IMAGE_MEDIA_TYPE = "image/jpeg"

# Dictionary keys
KEY_TYPE = "type"
KEY_ROLE = "role"
KEY_CONTENT = "content"
KEY_SOURCE = "source"
KEY_MEDIA_TYPE = "media_type"
KEY_DATA = "data"

# Configuration names
CONFIG_NAME_DEFAULT = "default"
CONFIG_NAME_FRIENDLY = "friendly"
CONFIG_NAME_NOT_FRIENDLY = "not-friendly"
CONFIG_NAME_TEST_INSULTS = "test-insults"
CONFIG_NAME_TEST_COMPLIMENTS = "test-compliments"

# Command constants
COMMAND_AI_SETMODE = "ai_setmode"
COMMAND_AI_LISTMODES = "ai_listmodes"
COMMAND_SETMODE_DESC = "Set the bot's response mode"
COMMAND_LISTMODES_DESC = "List all available response modes"

# Response format strings
LISTMODES_HEADER = "**Eshay bah! Here's all me different moods ay:**\n"
LISTMODES_NAME_FORMAT = "\n**{name}**"
LISTMODES_CHANCE_FORMAT = "\n- Chance of me poppin' off: {chance:.1f}%"
LISTMODES_RATIO_FORMAT = "\n- Ratio of insults to compliments: {insult:.0f}/{compliment:.0f}"
LISTMODES_SEPARATOR = "\n- - - - - - - - - -"

# File type constants
TEXT_FILE_EXTENSIONS = ('.txt', '.py', '.js', '.html', '.css', '.json', '.xml', '.md')

# Model constants
DEFAULT_MODEL = "claude-haiku-4-5-20251001"
DEFAULT_MAX_TOKENS = 8192
DEFAULT_TEMPERATURE = 0.8
BRIEF_MAX_TOKENS = 150
BRIEF_TEMPERATURE = 0.9

# Probability configurations
DEFAULT_CONFIG = {
    "name": CONFIG_NAME_DEFAULT,
    "total_chance": 0.002,
    "insult_weight": 0.5,
    "compliment_weight": 0.5
}

FRIENDLY_CONFIG = {
    "name": CONFIG_NAME_FRIENDLY,
    "total_chance": 0.01,
    "insult_weight": 0,
    "compliment_weight": 1
}

NOT_FRIENDLY_CONFIG = {
    "name": CONFIG_NAME_NOT_FRIENDLY,
    "total_chance": 0.01,
    "insult_weight": 1,
    "compliment_weight": 0
}

# Test configurations for image feature
TEST_INSULTS_CONFIG = {
    "name": CONFIG_NAME_TEST_INSULTS,
    "total_chance": 1.0,  # 100% chance to respond
    "insult_weight": 1,   # 100% insults
    "compliment_weight": 0
}

TEST_COMPLIMENTS_CONFIG = {
    "name": CONFIG_NAME_TEST_COMPLIMENTS,
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
