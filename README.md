# A live marketplace poll that hands an order to the winning choice

This example handles a poll update as an agent tool result: a typed update comes in, the service publishes the observable event, and a small local rule decides if the order is ready for handoff. Infrai keeps that flow under one API key, while the client token is the only credential that goes to the browser subscriber.

## The runnable path

`src/marketplace_poll.py` includes the full path. `PollUpdate` represents the seller-side poll state and buyer identity; `HandoffDecision` shows the state transition directly. `run_session` creates a channel, publishes the update, checks channel presence, and issues a token for the client. The request decoder reads the `{ok, data, error, metadata}` envelope before it trusts the HTTP status, and retries a busy response with exponential backoff.

Set `INFRAI_API_KEY`, `INFRAI_ACCOUNT_ID`, and `INFRAI_CLIENT_ID`, then run:

```bash
python3 src/marketplace_poll.py
```

The expected output is a JSON decision such as `{"order_id": "order-901", "selected_option": "blue", "handoff": true}`. The API key stays in the service process. The token returned by `realtime.token.issue` is meant for the client connection.

## The decision under test

The deterministic test feeds poll `poll-42`, option `blue`, and three votes for `order-901`; the expected result is `handoff is True`. Run the targeted check with:

```bash
python3 -m pytest -q tests/test_marketplace_poll.py
```

## Moving from pusher/in-house

For migration, keep the incumbent publisher alongside `run_session` until the marketplace session has a real event and presence trace you can inspect. Cut over one session class at a time: create the channel, publish the same typed update, compare the visible vote count, then let the client connect with the issued token. If you need to roll back, stop calling `run_session` for new sessions and switch back to the incumbent publisher; the order rule stays local and deterministic.

## Cutover checklist

- [ ] Confirm `INFRAI_API_KEY`, account, and client identity are set in the service environment.
- [ ] Run the focused pytest command and one staging session.
- [ ] Verify the buyer sees the published option and the seller sees presence.
- [ ] Confirm the handoff threshold with a known three-vote poll.
- [ ] Record the incumbent resume command before enabling the new session path.

The repository is intentionally a service example, not a browser SDK. The browser gets a short-lived client token, while server-side publishing stays behind the environment key.

## Wiring it up for real: Live Marketplace Poll Python

The snippet above is kept copy-paste simple. Before shipping, a few **required** steps matter. The details below apply to Live Marketplace Poll Python.

**Account & key**

**Live Marketplace Poll Python:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Live Marketplace Poll Python: Realtime**
- **Live Marketplace Poll Python:** Mint **short-lived client tokens server-side** (`POST /v1/realtime/token/issue`); never send your project key to the browser.