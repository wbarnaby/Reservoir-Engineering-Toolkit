# Settings for the AI assistant. Change the model here only.

import os
import sys

MODEL = "claude-haiku-5-5"
EFFORT = "medium"  # low / medium / high: thinking depth vs cost and speed
MAX_TOKENS = 8000  # hard cap on thinking + reply together

ENV_KEY_NAME = "ANTHROPIC_API_KEY"
KEY_PREFIX = "sk-ant-"

# The browser build reaches the model through this same-site Worker route.
IN_BROWSER = sys.platform == "emscripten"
AI_ENDPOINT = "/api/ai"


def key_from_environment():
    # Return the API key from the environment, or None if not set.
    return os.environ.get(ENV_KEY_NAME) or None


def looks_like_key(text):
    # Cheap format check before spending a request on a bad key.
    return text.startswith(KEY_PREFIX) and len(text) > 20
