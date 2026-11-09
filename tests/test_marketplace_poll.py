from src.marketplace_poll import PollUpdate, decide_handoff


def test_poll_reaches_order_handoff_threshold() -> None:
    update = PollUpdate("poll-42", "blue", 3, "buyer-17", "order-901")

    decision = decide_handoff(update)

    assert decision.order_id == "order-901"
    assert decision.selected_option == "blue"
    assert decision.handoff is True
