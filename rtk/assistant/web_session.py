"""One conversation in the browser build, through the site's AI endpoint.

The anthropic package cannot run under Pyodide, and the API key must
never reach the browser, so this talks to the Worker in web/worker.
Cloudflare Access checks the service token sent with every request.

Same interface as session.ChatSession, so the console can use either.
"""

import json
from types import SimpleNamespace

from rtk.assistant import config

REJECTED = "Cloudflare Access rejected these credentials."
UNREACHABLE = "Could not reach the AI service. Check your connection."
NO_REPLY = "The assistant returned no reply. Try rephrasing the question."


class GatewayError(Exception):
    # The AI endpoint failed; the message is written for the user.
    pass


class AccessDenied(GatewayError):
    # Cloudflare Access refused the credentials.
    pass


def browser_fetch(url, **options):
    # The real fetch, imported late because only Pyodide has it.
    from pyodide.http import pyfetch

    return pyfetch(url, **options)


async def read_lines(response):
    # Yield each line of a streamed response body as soon as it is whole.
    reader = response.js_response.body.getReader()
    buffer = b""
    while True:
        chunk = await reader.read()
        if chunk.done:
            break
        buffer += chunk.value.to_bytes()
        *lines, buffer = buffer.split(b"\n")
        for line in lines:
            if line:
                yield line
    if buffer:
        yield buffer


async def error_for(response):
    # Turn a failed response into the exception the user should see.
    status = response.status
    # 0 is a redirect to a login page, seen as opaque because redirects
    # are not followed. Access does this when strict mode is off.
    if status in (0, 401, 403):
        return AccessDenied(REJECTED)
    if status == 413:
        return GatewayError("Conversation too long. Type :clear to reset.")
    if status == 429:
        return GatewayError("Rate limit hit. Wait a moment and try again.")
    if status == 503:
        return GatewayError("The AI service is not set up on this site.")
    try:
        detail = json.loads(await response.text())["error"]
    except (ValueError, KeyError, TypeError):
        detail = f"AI service error ({status})."
    return GatewayError(detail)


class WebChatSession:
    # Holds the Access credentials and message history for one chat.

    errors = GatewayError

    def __init__(self, client_id, client_secret, fetch=None):
        # fetch can be passed in so tests can use a fake one
        self.fetch = fetch or browser_fetch
        self.headers = {
            "CF-Access-Client-Id": client_id,
            "CF-Access-Client-Secret": client_secret,
        }
        self.history = []
        self.last_usage = None

    async def request(self, **options):
        # Send one request with the credentials; raise unless it succeeds.
        headers = {**self.headers, **options.pop("headers", {})}
        try:
            response = await self.fetch(
                config.AI_ENDPOINT,
                headers=headers,
                # No cookies and no redirects, so a request is only ever
                # approved on the token it carries. Otherwise a session
                # cookie from Access would outlive a revoked token.
                credentials="omit",
                redirect="manual",
                **options,
            )
        except Exception as err:
            raise GatewayError(UNREACHABLE) from err
        if response.status != 200:
            raise await error_for(response)
        return response

    async def verify(self):
        # Ask Access to approve the credentials before AI mode opens.
        response = await self.request(method="GET")
        try:
            approved = json.loads(await response.text())["ok"] is True
        except (ValueError, KeyError, TypeError):
            approved = False
        if not approved:
            raise AccessDenied(REJECTED)

    async def reply(self, user_text):
        # Send user_text and yield the reply in pieces as it streams.
        self.history.append({"role": "user", "content": user_text})
        parts = []
        usage = {}
        try:
            response = await self.request(
                method="POST",
                headers={"Content-Type": "application/json"},
                body=json.dumps({"messages": self.history}),
            )
            try:
                async for line in read_lines(response):
                    event = json.loads(line)
                    if event["type"] == "message_start":
                        usage.update(event["message"]["usage"])
                    elif event["type"] == "message_delta":
                        usage.update(event["usage"])
                    elif event["type"] == "content_block_delta":
                        if event["delta"]["type"] == "text_delta":
                            parts.append(event["delta"]["text"])
                            yield event["delta"]["text"]
            except Exception as err:  # the stream broke or was cut short
                raise GatewayError(UNREACHABLE) from err
            if not parts:  # a refusal, or thinking used the whole budget
                raise GatewayError(NO_REPLY)
        except BaseException:
            # the question got no answer, so remove it to keep history valid
            self.history.pop()
            raise

        self.history.append({"role": "assistant", "content": "".join(parts)})
        self.last_usage = SimpleNamespace(**usage)

    def reset(self):
        # Forget the conversation.
        self.history.clear()

    def explain(self, err):
        # Return the line to show, and whether the user is now locked out.
        return str(err), isinstance(err, AccessDenied)
