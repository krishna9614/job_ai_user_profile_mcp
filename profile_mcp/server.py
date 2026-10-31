"""JobAI User Profile MCP server.

Exposes exactly three tools. None accepts a user id: the user is identified only by the
bearer token on the incoming MCP HTTP request, which is verified by the profile service.
"""

import logging
import os
from collections.abc import Mapping

from dotenv import load_dotenv
from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from profile_mcp.service_client import ProfileServiceClient, ProfileServiceError

load_dotenv()

logger = logging.getLogger("jobai.profile_mcp")

JOBAI_API_URL = os.getenv("JOBAI_API_URL", "http://127.0.0.1:8000")

mcp = MCPServer(
    name="jobai-user-profile",
    instructions="Read and manage the authenticated JobAI user's own profile.",
)
service = ProfileServiceClient(JOBAI_API_URL)


def bearer_token(headers: Mapping[str, str] | None) -> str:
    """Extract the caller's bearer token from the MCP request headers."""
    value = None
    for key, val in (headers or {}).items():
        if key.lower() == "authorization":
            value = val
            break
    scheme, _, token = (value or "").partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise ToolError("Not authenticated: missing bearer token")
    return token.strip()


def _tool_error(exc: ProfileServiceError) -> ToolError:
    if exc.status_code in (401, 403):
        return ToolError("Not authenticated or not allowed")
    return ToolError(exc.message)


def _call(fn, *args):
    try:
        return fn(*args)
    except ProfileServiceError as exc:
        raise _tool_error(exc) from exc


def _present(**fields) -> dict:
    return {k: v for k, v in fields.items() if v is not None}


@mcp.tool()
def get_user_profile(ctx: Context) -> dict:
    """Get the signed-in user's profile. Returns {"profile": null} if none exists yet."""
    token = bearer_token(ctx.headers)
    try:
        return {"profile": service.get_profile(token)}
    except ProfileServiceError as exc:
        if exc.status_code == 404:
            return {"profile": None, "message": "No profile has been created yet."}
        raise _tool_error(exc) from exc


@mcp.tool()
def create_user_profile(
    ctx: Context,
    first_name: str,
    middle_name: str | None = None,
    last_name: str | None = None,
    preferred_name: str | None = None,
    phone_country_code: str | None = None,
    phone_number: str | None = None,
    city: str | None = None,
    state_province: str | None = None,
    country_code: str | None = None,
    professional_headline: str | None = None,
    professional_summary: str | None = None,
    linkedin_url: str | None = None,
    github_url: str | None = None,
) -> dict:
    """Create the signed-in user's profile. Only call after the user explicitly asks."""
    token = bearer_token(ctx.headers)
    fields = _present(
        first_name=first_name,
        middle_name=middle_name,
        last_name=last_name,
        preferred_name=preferred_name,
        phone_country_code=phone_country_code,
        phone_number=phone_number,
        city=city,
        state_province=state_province,
        country_code=country_code,
        professional_headline=professional_headline,
        professional_summary=professional_summary,
        linkedin_url=linkedin_url,
        github_url=github_url,
    )
    return {"profile": _call(service.create_profile, token, fields)}


@mcp.tool()
def update_user_profile(
    ctx: Context,
    first_name: str | None = None,
    middle_name: str | None = None,
    last_name: str | None = None,
    preferred_name: str | None = None,
    phone_country_code: str | None = None,
    phone_number: str | None = None,
    city: str | None = None,
    state_province: str | None = None,
    country_code: str | None = None,
    professional_headline: str | None = None,
    professional_summary: str | None = None,
    linkedin_url: str | None = None,
    github_url: str | None = None,
) -> dict:
    """Update fields of the signed-in user's profile. Only provided fields change.
    Only call after the user explicitly asks."""
    token = bearer_token(ctx.headers)
    fields = _present(
        first_name=first_name,
        middle_name=middle_name,
        last_name=last_name,
        preferred_name=preferred_name,
        phone_country_code=phone_country_code,
        phone_number=phone_number,
        city=city,
        state_province=state_province,
        country_code=country_code,
        professional_headline=professional_headline,
        professional_summary=professional_summary,
        linkedin_url=linkedin_url,
        github_url=github_url,
    )
    if not fields:
        raise ToolError("Provide at least one field to update")
    return {"profile": _call(service.update_profile, token, fields)}
