# CIP Proto Logging Guide

This version adds conditional verbose logging for prototype testing.

The goal is to detect:

- what worked during a session,
- what failed,
- warnings such as empty messages or invalid actions,
- WebSocket connection/disconnection events,
- facilitator actions,
- participant messages,
- admin/replay loading actions,
- internal traces when agents use `log_trace()`.

## 1. Enable or disable logging from `.env`

Create your `.env` file if it does not exist:

```powershell
copy .env.example .env
notepad .env
```

To enable verbose logs during prototype testing:

```env
PROTO_MODE=True
PROTO_VERBOSE_LOGGING=True
PROTO_LOG_TO_CONSOLE=True
PROTO_LOG_PAYLOAD_MAX_CHARS=4000
```

To disable verbose logs outside prototype mode:

```env
PROTO_MODE=False
PROTO_VERBOSE_LOGGING=False
```

Then restart the server:

```powershell
CTRL + C
uvicorn cip.main:app --reload
```

## 2. Where logs are stored

The verbose session logs are stored in SQLite:

```text
cip.sqlite3
```

The new table is:

```text
session_logs
```

The app also writes summarized proto records into:

```text
traces
```

Normal chat/replay data is still saved in:

```text
messages
events
sessions
participants
injections
```

## 3. Important difference between normal data and proto logs

Normal data is always saved because the app needs it for replay and transcript:

- messages,
- sessions,
- participants,
- events,
- injections.

Verbose debug logs are saved only when:

```env
PROTO_MODE=True
PROTO_VERBOSE_LOGGING=True
```

So in production/pilot mode, you can disable verbose logging without breaking the session transcript.

## 4. How to view logs in the UI

Start the server:

```powershell
uvicorn cip.main:app --reload
```

Open the Admin dashboard:

```text
http://localhost:8000/admin
```

Select a session. You will see a new section:

```text
Verbose proto session logs
```

You can filter by:

- `INFO`
- `WARNING`
- `ERROR`

You can also open replay:

```text
http://localhost:8000/replay?session_id=YOUR_SESSION_ID
```

The replay page now includes:

```text
Verbose proto logs
```

## 5. How to access logs through API

All logs for one session:

```text
http://localhost:8000/admin/api/session-logs?session_id=YOUR_SESSION_ID
```

Only errors:

```text
http://localhost:8000/admin/api/session-logs?session_id=YOUR_SESSION_ID&level=ERROR
```

Only warnings:

```text
http://localhost:8000/admin/api/session-logs?session_id=YOUR_SESSION_ID&level=WARNING
```

Session traces:

```text
http://localhost:8000/admin/api/traces?session_id=YOUR_SESSION_ID
```

Replay data including messages, traces and logs:

```text
http://localhost:8000/admin/api/replay?session_id=YOUR_SESSION_ID
```

## 6. What is logged

### Session start

When the facilitator starts a session, the system logs:

- generated session ID,
- topic,
- configuration,
- created timestamp.

### Participant activity

The system logs:

- participant WebSocket connected,
- participant registered or seen,
- system connection confirmation sent,
- raw WebSocket payload received,
- message saved,
- message broadcast completed,
- participant WebSocket disconnected.

### Warnings

The system logs warnings for cases such as:

- empty participant message,
- invalid phase request,
- empty facilitator injection,
- stale WebSocket connections removed.

### Errors

The system logs errors for cases such as:

- missing session,
- database save failure,
- WebSocket loop exception,
- failed broadcast.

When possible, the error log includes:

- exception type,
- exception message,
- traceback.

## 7. Database inspection with PowerShell

From the project folder:

```powershell
python -c "import sqlite3; con=sqlite3.connect('cip.sqlite3'); print(con.execute('SELECT id, session_id, level, action, actor, status, created_at FROM session_logs ORDER BY id DESC LIMIT 20').fetchall())"
```

For one session:

```powershell
python -c "import sqlite3; con=sqlite3.connect('cip.sqlite3'); sid='YOUR_SESSION_ID'; print(con.execute('SELECT level, action, actor, status, message, created_at FROM session_logs WHERE session_id=? ORDER BY id', (sid,)).fetchall())"
```

## 8. Recommended prototype test flow

1. Set `.env`:

```env
PROTO_MODE=True
PROTO_VERBOSE_LOGGING=True
```

2. Restart server:

```powershell
uvicorn cip.main:app --reload
```

3. Open facilitator:

```text
http://localhost:8000/facilitator
```

4. Start a session.

5. Open participant link.

6. Send normal messages and also test edge cases:

- empty message,
- phase change,
- devil advocate,
- content injection,
- replay view,
- admin report view.

7. Open admin dashboard and inspect:

```text
Verbose proto session logs
```

8. When prototype testing is finished, disable verbose logs:

```env
PROTO_MODE=False
PROTO_VERBOSE_LOGGING=False
```

## 9. Files modified

```text
.env.example
cip/config.py
cip/db.py
cip/observability.py
cip/main.py
cip/facilitator/routes.py
cip/admin/routes.py
cip/websocket/manager.py
cip/templates/admin/dashboard.html
cip/templates/replay/session.html
cip/static/css/style.css
PROTO_LOGGING_GUIDE.md
```

## 10. Git commands to push this change

```powershell
git checkout -b proto-verbose-logging
git add .
git commit -m "Add proto-only verbose session logging"
git push -u origin proto-verbose-logging
```
