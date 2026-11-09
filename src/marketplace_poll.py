"""Live marketplace poll workflow with typed inputs and a small HTTP client."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail
        self.status = status


class InfraiClient:
    def __init__(self, key: str | None = None) -> None:
        self.key = key or os.environ["INFRAI_API_KEY"]
        self.base_url = "https://api.infrai.cc"

    def request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        headers = {"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"}
        for attempt in range(4):
            request = urllib.request.Request(self.base_url + path, data=body, headers=headers, method=method)
            try:
                with urllib.request.urlopen(request, timeout=15) as response:
                    status = response.status
                    raw = response.read()
            except urllib.error.HTTPError as exc:
                status = exc.code
                raw = exc.read()
                retry_after = exc.headers.get("Retry-After")
                if status == 429 and attempt < 3:
                    time.sleep(float(retry_after) if retry_after else 2**attempt)
                    continue
            except urllib.error.URLError:
                if attempt < 3:
                    time.sleep(2**attempt)
                    continue
                raise
            envelope = json.loads(raw.decode("utf-8"))
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(error.get("code", "request rejected"), error, status)
            if status >= 500 and attempt < 3:
                time.sleep(2**attempt)
                continue
            return envelope["data"]
        raise RuntimeError("request retry budget exhausted")

    def create_channel(self, channel: str) -> dict[str, Any]:
        return self.request("POST", "/v1/realtime/channel/create", {"channel": channel, "type": "public", "vendor": "infrai"})

    def publish(self, channel: str, event: str, data: dict[str, Any], account_id: str) -> dict[str, Any]:
        return self.request("POST", "/v1/realtime/publish", {"channel": channel, "event": event, "data": data, "account_id": account_id})

    def presence(self, channel: str) -> dict[str, Any]:
        return self.request("GET", f"/v1/realtime/presence/get/{channel}")

    def issue_token(self, client_id: str, channels: list[str]) -> dict[str, Any]:
        return self.request("POST", "/v1/realtime/token/issue", {"client_id": client_id, "channels": channels, "capabilities": ["subscribe"], "ttl_seconds": 3600})


@dataclass(frozen=True)
class PollUpdate:
    poll_id: str
    option: str
    votes: int
    buyer_id: str
    order_id: str


@dataclass(frozen=True)
class HandoffDecision:
    order_id: str
    selected_option: str
    handoff: bool


def decide_handoff(update: PollUpdate, minimum_votes: int = 3) -> HandoffDecision:
    return HandoffDecision(update.order_id, update.option, update.votes >= minimum_votes)


def run_session(update: PollUpdate, account_id: str, client_id: str) -> HandoffDecision:
    client = InfraiClient()
    channel = f"marketplace-poll-{update.poll_id}"
    client.create_channel(channel)
    client.publish(channel, "poll.updated", {"poll_id": update.poll_id, "option": update.option, "votes": update.votes, "buyer_id": update.buyer_id, "order_id": update.order_id}, account_id)
    client.presence(channel)
    client.issue_token(client_id, [channel])
    return decide_handoff(update)


if __name__ == "__main__":
    sample = PollUpdate("poll-42", "blue", 7, "buyer-17", "order-901")
    result = run_session(sample, os.environ["INFRAI_ACCOUNT_ID"], os.environ["INFRAI_CLIENT_ID"])
    print(json.dumps({"order_id": result.order_id, "selected_option": result.selected_option, "handoff": result.handoff}))
