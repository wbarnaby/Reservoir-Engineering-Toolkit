"""Tests for rtk.assistant, using a fake client (no network, no cost)."""

import asyncio

import pytest

from rtk.assistant.config import looks_like_key
from rtk.assistant.session import ChatSession


class FakeUsage:
    # Minimal stand-in for the SDK usage object.
    def __init__(self, input_tokens, output_tokens):
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens


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
            usage = FakeUsage(10, 5)

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


# ---------- usage metering ----------


def test_cost_of_sonnet():
    from rtk.assistant.usage import cost_of

    # 1000 input at $2/M + 500 output at $10/M = 0.002 + 0.005
    counts = {"input": 1000, "output": 500, "cache_write": 0, "cache_read": 0}
    assert cost_of(counts, "claude-sonnet-5-5") == pytest.approx(0.007)


def test_cost_of_unknown_model():
    from rtk.assistant.usage import cost_of

    with pytest.raises(ValueError, match="No prices"):
        cost_of(
            {"input": 1, "output": 0, "cache_write": 0, "cache_read": 0},
            "gpt-4",
        )


def test_read_usage_handles_missing_cache_fields():
    from rtk.assistant.usage import read_usage

    counts = read_usage(FakeUsage(100, 50))
    assert counts == {
        "input": 100,
        "output": 50,
        "cache_write": 0,
        "cache_read": 0,
    }


def test_meter_accumulates():
    from rtk.assistant.usage import UsageMeter

    meter = UsageMeter("claude-sonnet-5-5")
    meter.record(FakeUsage(1000, 500))
    meter.record(FakeUsage(2000, 1000))

    assert meter.last.tokens == 3000
    assert meter.total.tokens == 4500
    assert meter.last.cost == pytest.approx(0.014)
    assert meter.total.cost == pytest.approx(0.021)


def test_meter_reset():
    from rtk.assistant.usage import UsageMeter

    meter = UsageMeter("claude-sonnet-5-5")
    meter.record(FakeUsage(1000, 500))
    meter.reset()
    assert meter.total.tokens == 0
    assert meter.last.cost == 0.0
