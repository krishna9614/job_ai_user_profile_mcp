import json

import httpx
import pytest
from mcp.server.mcpserver.exceptions import ToolError

from profile_mcp import server
from profile_mcp.service_client import ProfileServiceClient


class FakeCtx:
    def __init__(self, headers):
        self.headers = headers


@pytest.fixture()
def backend(monkeypatch):
    """Mock profile service; records requests and serves one profile per token."""
    profiles: dict[str, dict] = {"ada-token": {"first_name": "Ada"}}
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        token = request.headers.get("authorization", "").removeprefix("Bearer ")
        if token not in ("ada-token", "bob-token"):
            return httpx.Response(401, json={"detail": "Invalid or expired access token"})
        if request.method == "GET":
            if token not in profiles:
                return httpx.Response(404, json={"detail": "Profile not found"})
            return httpx.Response(200, json=profiles[token])
        if request.method == "POST":
            if token in profiles:
                return httpx.Response(409, json={"detail": "Profile already exists"})
            profiles[token] = json.loads(request.content)
            return httpx.Response(201, json=profiles[token])
        profiles[token].update(json.loads(request.content))
        return httpx.Response(200, json=profiles[token])

    client = ProfileServiceClient("http://backend", transport=httpx.MockTransport(handler))
    monkeypatch.setattr(server, "service", client)
    return calls


def auth(token):
    return FakeCtx({"Authorization": f"Bearer {token}"})


def test_tools_have_no_user_id_parameter():
    import inspect

    for fn in (server.get_user_profile, server.create_user_profile, server.update_user_profile):
        assert "user_id" not in inspect.signature(fn).parameters


@pytest.mark.parametrize("headers", [None, {}, {"Authorization": "Basic x"}, {"authorization": "Bearer "}])
def test_missing_token_rejected(backend, headers):
    with pytest.raises(ToolError, match="Not authenticated"):
        server.get_user_profile(FakeCtx(headers))
    assert backend == []


def test_get_forwards_callers_token(backend):
    assert server.get_user_profile(auth("ada-token")) == {"profile": {"first_name": "Ada"}}
    assert backend[-1].url.path == "/api/v1/users/me/profile"
    assert backend[-1].headers["authorization"] == "Bearer ada-token"


def test_get_missing_profile(backend):
    assert server.get_user_profile(auth("bob-token"))["profile"] is None


def test_invalid_token(backend):
    with pytest.raises(ToolError, match="Not authenticated"):
        server.get_user_profile(auth("forged"))


def test_create_and_update(backend):
    created = server.create_user_profile(auth("bob-token"), first_name="Bob", city="Paris")
    assert created["profile"] == {"first_name": "Bob", "city": "Paris"}
    with pytest.raises(ToolError, match="already exists"):
        server.create_user_profile(auth("bob-token"), first_name="Bob")
    updated = server.update_user_profile(auth("bob-token"), city="Berlin")
    assert updated["profile"]["city"] == "Berlin"
    assert json.loads(backend[-1].content) == {"city": "Berlin"}
    with pytest.raises(ToolError):
        server.update_user_profile(auth("bob-token"))


def test_only_three_tools_registered():
    import asyncio

    tools = asyncio.run(server.mcp.list_tools())
    assert sorted(t.name for t in tools) == [
        "create_user_profile",
        "get_user_profile",
        "update_user_profile",
    ]
    for tool in tools:
        assert "user_id" not in json.dumps(tool.input_schema)
