from types import SimpleNamespace as NS

from tradebot.agent import TradingAgent


class FakeMessages:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append({**kwargs, "messages": list(kwargs["messages"])})
        return self.responses.pop(0)


def resp(stop, *blocks):
    return NS(stop_reason=stop, content=list(blocks),
              usage=NS(input_tokens=10, output_tokens=5, cache_read_input_tokens=0))


def tool(id_, name, input_):
    return NS(type="tool_use", id=id_, name=name, input=input_)


def text(t):
    return NS(type="text", text=t)


def test_agent_loop_places_order_and_saves_notes(env):
    msgs = FakeMessages([
        resp("tool_use", tool("t1", "get_account", {}), tool("t2", "get_quotes", {"symbols": ["AAPL"]})),
        resp("tool_use", tool("t3", "place_order", {"symbol": "AAPL", "side": "buy", "order_type": "market",
                                                    "notional_usd": 500, "rationale": "trend; stop 185; target 230"})),
        resp("tool_use", tool("t4", "update_notes", {"text": "AAPL: stop 185, target 230"})),
        resp("end_turn", text("Bought $500 AAPL.")),
    ])
    client = NS(beta=NS(messages=msgs))
    agent = TradingAgent(env["settings"], env["ex"], env["notes"], env["journal"], client=client)
    result = agent.run_session(verbose=False)

    assert result.stop_reason == "end_turn"
    assert result.summary == "Bought $500 AAPL."
    assert len(result.orders) == 1 and result.orders[0]["result"]["status"] == "filled"
    assert env["notes"].text.startswith("AAPL")

    first = msgs.calls[0]
    assert first["model"] == "claude-opus-5-5"
    assert first["thinking"] == {"type": "adaptive"}
    assert first["fallbacks"] == "default"
    # Both tool results from the parallel calls go back in one user message.
    second_msgs = msgs.calls[1]["messages"]
    assert [b["tool_use_id"] for b in second_msgs[-1]["content"]] == ["t1", "t2"]
    # Next session sees the last summary and the notes.
    assert "Bought $500 AAPL." in agent._kickoff(None)
    assert "stop 185" in agent._kickoff(None)


def test_blocked_order_is_reported_as_tool_error(env):
    msgs = FakeMessages([
        resp("tool_use", tool("t1", "place_order", {"symbol": "AAPL", "side": "buy", "order_type": "market",
                                                    "notional_usd": 5000, "rationale": "too big"})),
        resp("end_turn", text("Skipped.")),
    ])
    agent = TradingAgent(env["settings"], env["ex"], env["notes"], env["journal"],
                         client=NS(beta=NS(messages=msgs)))
    agent.run_session(verbose=False)
    result_block = msgs.calls[1]["messages"][-1]["content"][0]
    assert result_block["is_error"] is True
    assert "max_order_usd" in result_block["content"]


def test_refusal_stops_session(env):
    msgs = FakeMessages([NS(stop_reason="refusal", content=[], stop_details=None,
                            usage=NS(input_tokens=1, output_tokens=0, cache_read_input_tokens=0))])
    agent = TradingAgent(env["settings"], env["ex"], env["notes"], env["journal"],
                         client=NS(beta=NS(messages=msgs)))
    result = agent.run_session(verbose=False)
    assert result.stop_reason == "refusal" and result.orders == []
