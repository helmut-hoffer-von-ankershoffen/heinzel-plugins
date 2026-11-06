"""Real SDK text, control and acknowledgement frames use fresh OS entropy without network activity."""

import json
import logging

import pytest

from heinzel_slack._vendor.slack_sdk.socket_mode import SocketModeClient
from heinzel_slack._vendor.slack_sdk.socket_mode.builtin import internals
from heinzel_slack._vendor.slack_sdk.socket_mode.builtin.connection import Connection
from heinzel_slack._vendor.slack_sdk.socket_mode.response import SocketModeResponse

pytestmark = pytest.mark.integration


class CapturedSocket:
    """Capture the actual SDK frame bytes instead of sending them to a server."""

    def __init__(self):
        self.frames = []

    def send(self, data):
        self.frames.append(data)
        return len(data)


@pytest.mark.parametrize("kind", ["text", "extended-text", "ping", "pong", "ack"])
def test_real_sdk_frames_request_four_fresh_os_bytes_and_roundtrip_the_payload(monkeypatch, kind):
    connection = Connection("wss://example.invalid/socket", logging.getLogger("mask-proof"))
    captured = CapturedSocket()
    connection.sock = captured
    # Avoid the SDK constructor's background threads; exercise its real response/send methods.
    client = SocketModeClient.__new__(SocketModeClient)
    client.current_session = connection
    client.logger = logging.getLogger("mask-proof")
    masks = [b"\x01\x82\x03\xff", b"\x91\x02\xfe\x04"]
    requested = []

    def entropy(length):
        requested.append(length)
        assert length == 4
        return masks[len(requested) - 1]

    def forbid_prng(*_args, **_kwargs):
        pytest.fail("Protocol masking must never use the pseudorandom generator")

    monkeypatch.setattr(internals.os, "urandom", entropy)
    monkeypatch.setattr(internals.random, "choices", forbid_prng)
    payload = "Hello, fictional workspace" if kind != "extended-text" else "x" * 126
    for _ in masks:
        if kind == "ack":
            client.send_socket_mode_response(SocketModeResponse(envelope_id="fictional-envelope"))
        elif kind == "ping":
            connection.ping(payload)
        elif kind == "pong":
            connection.pong(payload)
        else:
            connection.send(payload)
    assert requested == [4, 4]
    assert len(captured.frames) == 2 and captured.frames[0] != captured.frames[1]
    for frame, mask in zip(captured.frames, masks, strict=True):
        assert frame[0] == 0x80 | {"ping": 9, "pong": 10}.get(kind, 1)
        assert frame[1] & 0x80
        length = frame[1] & 0x7F
        offset = 2
        if length == 126:
            length = int.from_bytes(frame[2:4], "big")
            offset = 4
        assert frame[offset : offset + 4] == mask
        body = frame[offset + 4 :]
        assert len(body) == length
        decoded = bytes(byte ^ mask[index % 4] for index, byte in enumerate(body)).decode()
        if kind == "ack":
            assert json.loads(decoded) == {"envelope_id": "fictional-envelope"}
        else:
            assert decoded == payload
