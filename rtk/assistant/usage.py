"""Token accounting and cost for th AI assistant.

Prices are per-token, derived from the per-million-token rates on
https://platform.claude.com/docs/en/about-claude/pricing and stored
in PRICES keyed by model. Update them if the rates change.
"""

from dataclasses import dataclass

# dollars per token = (dollars per million) / 1e6
PRICES = {
    "claude-sonnet-5-5": {
        "input": 2.0 / 1e6,
        "output": 10.0 / 1e6,
        "cache_write": 2.50 / 1e6,
        "cache_read": 0.10 / 1e6,
    },
    "claude-haiku-5-5": {
        "input": 0.10 / 1e6,
        "output": 0.50 / 1e6,
        "cache_write": 0.125 / 1e6,
        "cache_read": 0.01 / 1e6,
    },
    "claude-opus-5-5": {
        "input": 4.0 / 1e6,
        "output": 20.0 / 1e6,
        "cache_write": 5.0 / 1e6,
        "cache_read": 0.20 / 1e6,
    },
}


@dataclass
class Turn:
    # Tokens and cost for one message exchange.

    tokens: int = 0
    cost: float = 0.0


def read_usage(usage):
    """Pull token counts off an SDK usage object into a plain dict.

    getattr with a default keeps this working when a field is absent,
    for example cache fields before prompt caching is turned on.
    """
    return {
        "input": getattr(usage, "input_tokens", 0) or 0,
        "output": getattr(usage, "output_tokens", 0) or 0,
        "cache_write": getattr(usage, "cache_creation_input_tokens", 0) or 0,
        "cache_read": getattr(usage, "cache_read_input_tokens", 0) or 0,
    }


def cost_of(counts, model):
    # Return the dollar cost of one message's token counts.
    if model not in PRICES:
        raise ValueError(f"No prices stored for model '{model}'")
    rates = PRICES[model]
    return sum(counts[part] * rates[part] for part in counts)


class UsageMeter:
    # Running totals plus the most recent turn.

    def __init__(self, model):
        self.model = model
        self.total = Turn()
        self.last = Turn()

    def record(self, usage):
        # Add one message's usage and update the last-turn figures.
        counts = read_usage(usage)
        tokens = sum(counts.values())
        cost = cost_of(counts, self.model)

        self.last = Turn(tokens, cost)
        self.total = Turn(self.total.tokens + tokens, self.total.cost + cost)
        return self.last

    def reset(self):
        # Zero the running totals (used when the chat is cleared).
        self.total = Turn()
        self.last = Turn()
