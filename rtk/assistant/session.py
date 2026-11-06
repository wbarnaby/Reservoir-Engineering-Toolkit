"""One conversation with the model: history plus streaming replies.

No Textual imports here, so this module can be tested without a UI.
"""

import anthropic

from rtk.assistant import config
from rtk.assistant.prompt import build_system_prompt


class ChatSession:
    # Holds the API client and the message history for one chat.

    def __init__(self, api_key, client=None):
        # client can be passed in so tests can use a fake one
        if client is None:
            client = anthropic.AsyncAnthropic(api_key=api_key)
        self.client = client
        self.history = []
        self.last_usage = None

    async def reply(self, user_text):
        # Send user_text and yield the reply in pieces as it streams.
        self.history.append({"role": "user", "content": user_text})
        try:
            async with self.client.messages.stream(
                model=config.MODEL,
                max_tokens=config.MAX_TOKENS,
                system=build_system_prompt(),
                messages=self.history,
                output_config={"effort": config.EFFORT},
            ) as stream:
                async for text in stream.text_stream:
                    yield text
                final = await stream.get_final_message()
        except BaseException:
            # the question got no answer, so remove it to keep history valid
            self.history.pop()
            raise

        self.history.append({"role": "assistant", "content": final.content})
        self.last_usage = final.usage

    def reset(self):
        # Forget the conversation.
        self.history.clear()


def friendly_error(err):  # noqa: N805
    # Turn an SDK exception into one line a user can act on.
    if isinstance(err, anthropic.AuthenticationError):
        return "API key rejected. Type AI again to enter a new key."
    if isinstance(err, anthropic.PermissionDeniedError):
        return "This key is not allowed to use that model."
    if isinstance(err, anthropic.RateLimitError):
        return "Rate limit hit. Wait a moment and try again."
    if isinstance(err, anthropic.APIConnectionError):
        return "Could not reach the API. Check your internet connection."
    if isinstance(err, anthropic.APIStatusError):
        return f"API error {err.status_code}: {err.message}"
    return f"Unexpected error: {err}"
