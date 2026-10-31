"""Client for the JobAI profile service (the FastAPI backend in job_ai_adk_agent).

The backend owns all profile business logic and SQL. This client forwards the caller's
own bearer token; the backend verifies it and derives the user from it, so a caller can
only ever act on their own profile.
"""

from typing import Any

import httpx

PROFILE_PATH = "/api/v1/users/me/profile"


class ProfileServiceError(Exception):
    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.message = message


class ProfileServiceClient:
    def __init__(
        self, base_url: str, *, timeout: float = 10.0, transport: httpx.BaseTransport | None = None
    ):
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._transport = transport

    def _request(self, method: str, access_token: str, json: dict | None = None) -> dict[str, Any]:
        try:
            with httpx.Client(
                base_url=self._base_url, timeout=self._timeout, transport=self._transport
            ) as client:
                resp = client.request(
                    method,
                    PROFILE_PATH,
                    json=json,
                    headers={"Authorization": f"Bearer {access_token}"},
                )
        except httpx.HTTPError as exc:
            raise ProfileServiceError(503, "Profile service is unavailable") from exc
        if resp.is_success:
            return resp.json()
        raise ProfileServiceError(resp.status_code, _error_message(resp))

    def get_profile(self, access_token: str) -> dict[str, Any]:
        return self._request("GET", access_token)

    def create_profile(self, access_token: str, fields: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", access_token, json=fields)

    def update_profile(self, access_token: str, fields: dict[str, Any]) -> dict[str, Any]:
        return self._request("PATCH", access_token, json=fields)


def _error_message(resp: httpx.Response) -> str:
    try:
        detail = resp.json().get("detail")
    except ValueError:
        detail = None
    if isinstance(detail, list):  # FastAPI validation errors
        return "; ".join(
            f"{'.'.join(str(p) for p in e.get('loc', [])[1:])}: {e.get('msg')}" for e in detail
        )
    return str(detail or resp.reason_phrase or "Profile service error")
