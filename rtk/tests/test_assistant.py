"""Tests for rtk.assistant, using a fake client (no network, no cost)."""

import asyncio

import pytest

from rtk.assistant.config import looks_like_key
from rtk.assistant.session import ChatSession


class FakeStream:
    """Stands in for the SDK's stream: yields fixed text pieces."""

    def __init__(self, pieces, fail=False):
        self.pieces = pieces
        self.fail = fail

    async def __aenter__(self):
        if self.fail:
            raise RuntimeError("network down")
        return self

    async def __aexit__(self, *exc_info):
        return False

    @property
    async def text_stream(self):
        for piece in self.pieces:
            yield piece

    async def get_final_message(self):
        class Final:
            content = [{"type": "text", "text": "".join(self.pieces)}]

        return Final()


class FakeMessages:
    def __init__(self, pieces, fail):
        self.pieces = pieces
        self.fail = fail
        self.last_kwargs = None

    def stream(self, **kwargs):
        self.last_kwargs = kwargs
        return FakeStream(self.pieces, self.fail)


class FakeClient:
    def __init__(self, pieces=("Hello", " there"), fail=False):
        self.messages = FakeMessages(pieces, fail)


async def collect(session, text):
    """Run one reply and return all streamed pieces joined."""
    return "".join([piece async for piece in session.reply(text)])


def test_reply_streams_text():
    session = ChatSession("unused", client=FakeClient())
    assert asyncio.run(collect(session, "hi")) == "Hello there"


def test_history_records_both_turns():
    session = ChatSession("unused", client=FakeClient())
    asyncio.run(collect(session, "hi"))
    roles = [message["role"] for message in session.history]
    assert roles == ["user", "assistant"]


def test_failed_request_leaves_history_clean():
    session = ChatSession("unused", client=FakeClient(fail=True))
    with pytest.raises(RuntimeError):
        asyncio.run(collect(session, "hi"))
    assert session.history == []


def test_request_uses_config():
    client = FakeClient()
    session = ChatSession("unused", client=client)
    asyncio.run(collect(session, "hi"))
    sent = client.messages.last_kwargs
    assert sent["model"].startswith("claude-")
    assert "effort" in sent["output_config"]
    assert "Reservoir Toolkit" in sent["system"]


def test_reset_clears_history():
    session = ChatSession("unused", client=FakeClient())
    asyncio.run(collect(session, "hi"))
    session.reset()
    assert session.history == []


@pytest.mark.parametrize(
    "text, expected",
    [
        ("sk-ant-api03-abcdefghijklmnop", True),
        ("sk-ant-", False),
        ("hello", False),
        ("", False),
    ],
)
def test_looks_like_key(text, expected):
    assert looks_like_key(text) is expected
