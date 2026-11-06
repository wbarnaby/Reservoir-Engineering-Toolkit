"""Tests for the browser chat session, using a fake fetch (no network)."""

import asyncio
import json

import pytest

from rtk.assistant.usage import read_usage
from rtk.assistant.web_session import (
    AccessDenied,
    GatewayError,
    WebChatSession,
)


def event_lines(*texts):
    # The events the Worker streams for a reply made of texts.
    events = [
        {
            "type": "message_start",
            "message": {"usage": {"input_tokens": 10, "output_tokens": 1}},
        },
        {
            "type": "content_block_delta",
            "delta": {"type": "thinking_delta", "thinking": "hmm"},
        },
    ]
    for text in texts:
        events.append(
            {
                "type": "content_block_delta",
                "delta": {"type": "text_delta", "text": text},
            }
        )
    events.append({"type": "message_delta", "usage": {"output_tokens": 7}})
    return b"".join(json.dumps(e).encode() + b"\n" for e in events)


class FakeChunk:
    def __init__(self, data):
        self.done = data is None
        self.value = self
        self.data = data

    def to_bytes(self):
        return self.data


class FakeReader:
    def __init__(self, chunks, fail):
        self.chunks = list(chunks)
        self.fail = fail

    async def read(self):
        if self.chunks:
            return FakeChunk(self.chunks.pop(0))
        if self.fail:
            raise RuntimeError("network lost")
        return FakeChunk(None)


class FakeBody:
    def __init__(self, chunks, fail):
        self.chunks = chunks
        self.fail = fail

    def getReader(self):  # noqa: N802 - name set by the browser
        return FakeReader(self.chunks, self.fail)


class FakeJsResponse:
    def __init__(self, chunks, fail):
        self.body = FakeBody(chunks, fail)


class FakeResponse:
    def __init__(self, status=200, text="", chunks=(), fail=False):
        self.status = status
        self.body_text = text
        self.js_response = FakeJsResponse(chunks, fail)

    async def text(self):
        return self.body_text


class FakeFetch:
    # Returns queued responses and records how it was called.

    def __init__(self, *responses, fail=False):
        self.responses = list(responses)
        self.fail = fail
        self.calls = []

    async def __call__(self, url, **options):
        self.calls.append((url, options))
        if self.fail:
            raise OSError("offline")
        return self.responses.pop(0)


def session_with(*responses, fail=False):
    fetch = FakeFetch(*responses, fail=fail)
    return WebChatSession("my-id", "my-secret", fetch=fetch), fetch


async def collect(session, text):
    return "".join([piece async for piece in session.reply(text)])


# ---------- approval ----------


def test_verify_passes_when_approved():
    session, fetch = session_with(FakeResponse(text='{"ok": true}'))
    asyncio.run(session.verify())
    assert fetch.calls[0][1]["method"] == "GET"


@pytest.mark.parametrize("status", [0, 401, 403])
def test_verify_denied_by_access(status):
    session, _ = session_with(FakeResponse(status, text="<html>no</html>"))
    with pytest.raises(AccessDenied):
        asyncio.run(session.verify())


@pytest.mark.parametrize("body", ["<html>login</html>", '{"ok": false}', "{}"])
def test_verify_needs_the_workers_answer(body):
    # a 200 that is not from the Worker must not unlock AI mode
    session, _ = session_with(FakeResponse(text=body))
    with pytest.raises(AccessDenied):
        asyncio.run(session.verify())


def test_verify_offline_is_not_a_rejection():
    session, _ = session_with(fail=True)
    with pytest.raises(GatewayError) as caught:
        asyncio.run(session.verify())
    assert not isinstance(caught.value, AccessDenied)


def test_every_request_carries_the_token_and_nothing_else():
    session, fetch = session_with(
        FakeResponse(text='{"ok": true}'),
        FakeResponse(chunks=[event_lines("Hi")]),
    )
    asyncio.run(session.verify())
    asyncio.run(collect(session, "hello"))
    assert len(fetch.calls) == 2
    for _url, options in fetch.calls:
        assert options["headers"]["CF-Access-Client-Id"] == "my-id"
        assert options["headers"]["CF-Access-Client-Secret"] == "my-secret"
        # a cookie or followed redirect could outlive a revoked token
        assert options["credentials"] == "omit"
        assert options["redirect"] == "manual"


# ---------- chat ----------


def test_reply_streams_text_only():
    session, _ = session_with(FakeResponse(chunks=[event_lines("Hel", "lo")]))
    assert asyncio.run(collect(session, "hi")) == "Hello"


def test_reply_handles_lines_split_across_chunks():
    data = event_lines("Hello", " there")
    chunks = [data[i : i + 7] for i in range(0, len(data), 7)]
    session, _ = session_with(FakeResponse(chunks=chunks))
    assert asyncio.run(collect(session, "hi")) == "Hello there"


def test_request_sends_only_the_conversation():
    session, fetch = session_with(FakeResponse(chunks=[event_lines("Hi")]))
    asyncio.run(collect(session, "hello"))
    sent = json.loads(fetch.calls[0][1]["body"])
    assert sent == {"messages": [{"role": "user", "content": "hello"}]}


def test_history_alternates_as_plain_text():
    session, fetch = session_with(
        FakeResponse(chunks=[event_lines("One")]),
        FakeResponse(chunks=[event_lines("Two")]),
    )
    asyncio.run(collect(session, "first"))
    asyncio.run(collect(session, "second"))
    sent = json.loads(fetch.calls[1][1]["body"])["messages"]
    assert [m["role"] for m in sent] == ["user", "assistant", "user"]
    assert sent[1]["content"] == "One"


def test_usage_feeds_the_meter():
    session, _ = session_with(FakeResponse(chunks=[event_lines("Hi")]))
    asyncio.run(collect(session, "hello"))
    counts = read_usage(session.last_usage)
    assert counts["input"] == 10
    assert counts["output"] == 7


@pytest.mark.parametrize(
    "response, error",
    [
        (FakeResponse(403), AccessDenied),
        (FakeResponse(429), GatewayError),
        (FakeResponse(502, text='{"error": "bad"}'), GatewayError),
        (FakeResponse(chunks=[b"not json\n"]), GatewayError),
        (FakeResponse(chunks=[event_lines()]), GatewayError),
        (FakeResponse(chunks=[event_lines("Hi")], fail=True), GatewayError),
    ],
)
def test_failed_reply_leaves_history_clean(response, error):
    session, _ = session_with(response)
    with pytest.raises(error):
        asyncio.run(collect(session, "hi"))
    assert session.history == []
    assert session.last_usage is None


def test_explain_locks_out_only_on_access_denied():
    session, _ = session_with()
    assert session.explain(AccessDenied("no"))[1] is True
    assert session.explain(GatewayError("busy"))[1] is False


def test_server_problem_shows_the_workers_message():
    session, _ = session_with(FakeResponse(502, text='{"error": "AI down"}'))
    with pytest.raises(GatewayError, match="AI down"):
        asyncio.run(collect(session, "hi"))
