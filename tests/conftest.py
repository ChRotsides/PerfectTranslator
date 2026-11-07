"""Shared fixtures: a fake OpenAI client so no test touches the network."""

from types import SimpleNamespace

import httpx
import openai
import pytest


class FakeClient:
    """Mimics ``client.chat.completions.create`` and records every call.

    ``replies`` is a list consumed in order; each item is either a string
    (returned as the message content), an exception instance (raised) or a
    callable that receives the call kwargs and returns a string (it may
    raise too). When the list runs out the last item is reused.
    """

    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        item = self.replies.pop(0) if len(self.replies) > 1 else (self.replies[0] if self.replies else "ok")
        if isinstance(item, Exception):
            raise item
        if callable(item):
            item = item(kwargs)
        message = SimpleNamespace(content=item)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def _response(status):
    return httpx.Response(status, request=httpx.Request("POST", "https://api.invalid/v1/chat/completions"))


def rate_limit_error():
    return openai.RateLimitError("slow down", response=_response(429), body=None)


def server_error():
    return openai.InternalServerError("boom", response=_response(500), body=None)


def auth_error():
    return openai.AuthenticationError("bad key", response=_response(401), body=None)


def connection_error():
    return openai.APIConnectionError(request=httpx.Request("POST", "https://api.invalid"))


@pytest.fixture
def no_sleep():
    """A sleep replacement that records requested delays instead of waiting."""
    delays = []
    return delays.append, delays
