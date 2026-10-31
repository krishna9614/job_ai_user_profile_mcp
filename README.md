# job_ai_user_profile_mcp

MCP server (streamable HTTP) for the authenticated JobAI user's profile. It is used by the
single ADK agent in [job_ai_adk_agent](https://github.com/krishna9614/job_ai_adk_agent).

## Tools

| Tool | Backend call |
|---|---|
| `get_user_profile` | `GET /api/v1/users/me/profile`. Returns `{"profile": null}` if no profile exists yet. |
| `create_user_profile` | `POST /api/v1/users/me/profile` (`first_name` is required) |
| `update_user_profile` | `PATCH /api/v1/users/me/profile` (only the fields you pass change) |

## Security model

- None of the tools takes a `user_id`. Each one reads the `Authorization: Bearer <Supabase access token>`
  header from the incoming MCP HTTP request and forwards it unchanged to the JobAI API.
- The API verifies the token and works out the user from it. A caller can only ever read or
  change their own profile. A missing token is rejected before any backend call. Invalid tokens
  are rejected by the API.
- All profile logic and SQL live in the JobAI API (`app/services/profile_service.py`). This repo
  only contains the HTTP client (`profile_mcp/service_client.py`), so no SQL is duplicated here.
- The ADK agent currently gets only `get_user_profile`. The write tools exist for callers
  that have explicit user authorization.

## Local setup and run

```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

python server.py      # http://127.0.0.1:8001/mcp (start the JobAI API on :8000 too)
pytest                # unit tests; the backend is mocked
```
