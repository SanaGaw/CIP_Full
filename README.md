# Collective Intelligence Platform v2 (CIP v2)

CIP v2 is a pilot FastAPI application for running structured collective-intelligence sessions. It provides four web interfaces:

- `/admin` — operator dashboard for monitoring sessions, traces, reports and configuration.
- `/facilitator` — workshop control panel for creating sessions, moving phases and injecting prompts.
- `/participant?session_id=...` — participant contribution room.
- `/replay?session_id=...` — replay and review page for session timelines.

## Quick start

```bash
pip install -r requirements.txt
copy .env.example .env      # Windows
# cp .env.example .env      # Linux/macOS
uvicorn cip.main:app --reload
```

Open:

```text
http://localhost:8000/facilitator
```

Create a session, copy the generated participant link, and share it with users.

## UI guide

Read the full guide here:

```text
UI_ACCESS_GUIDE.md
```

It explains how to access each interface and how to use each main parameter.

## Project structure

```text
cip/
  admin/            Admin API routes
  facilitator/      Facilitator API routes
  agents/           Agent and orchestration stubs
  engines/          Decision and criteria engines
  llm/              LLM clients and tier routing
  nlp/              NLP utilities
  static/css/       Shared UI styling
  templates/        Admin, facilitator, participant and replay pages
  websocket/        WebSocket connection manager
```

## Important pilot limitation

The UI is upgraded and the core session/message flow is usable, but the platform is still a pilot. Authentication is not enforced yet, and advanced agent logic/report generation remains incomplete.

Do not deploy this version publicly without adding authentication and access control.

## Proto verbose logging

This branch supports conditional verbose logging for prototype sessions.

Enable in `.env`:

```env
PROTO_MODE=True
PROTO_VERBOSE_LOGGING=True
PROTO_LOG_TO_CONSOLE=True
PROTO_LOG_PAYLOAD_MAX_CHARS=4000
```

Disable outside prototype testing:

```env
PROTO_MODE=False
PROTO_VERBOSE_LOGGING=False
```

Logs are stored in SQLite table `session_logs` and can be viewed from `/admin` or through:

```text
/admin/api/session-logs?session_id=YOUR_SESSION_ID
```

See `PROTO_LOGGING_GUIDE.md` for full usage.
