# CIP UI Upgrade — Access and Parameter Guide

This guide explains how to run the upgraded CIP interface, how to access each role screen, and how to use the main parameters.

## 1. What was upgraded

The UI upgrade adds a cleaner, more usable interface for:

- **Admin dashboard**: global supervision, sessions, telemetry, traces, transcript preview, report preview, safe configuration view.
- **Facilitator dashboard**: session creation, workshop parameters, phase control, challenge prompts, content injection, session links and live state.
- **Participant room**: simple chat room for participants with quick prompts and reconnect controls.
- **Replay viewer**: session timeline, message replay, phases, ideas and trace log.

The upgrade also adds/fixes minimal backend endpoints needed by the UI:

- `/replay` page route.
- `/admin/api/sessions` to list sessions.
- SQLite-compatible admin/facilitator APIs.
- `/ws/{session_id}/{participant_id}` WebSocket for participants.
- `/api/session/{session_id}/message` HTTP fallback for message saving.
- Missing pilot database tables: `sessions`, `participants`, `messages`, `ideas`, `clusters`, `injections`.

## 2. Files changed or added

Copy these files into your project if you want to apply only the UI upgrade:

```text
cip/main.py
cip/db.py
cip/config.py
cip/admin/routes.py
cip/facilitator/routes.py
cip/websocket/manager.py
cip/static/css/style.css
cip/templates/admin/dashboard.html
cip/templates/facilitator/dashboard.html
cip/templates/participant/chat.html
cip/templates/replay/session.html
UI_ACCESS_GUIDE.md
```

## 3. Run locally

From the project root:

```bash
pip install -r requirements.txt
copy .env.example .env      # Windows PowerShell/CMD
# or: cp .env.example .env  # Linux/macOS
uvicorn cip.main:app --reload
```

Then open:

```text
http://localhost:8000
```

The root page returns a small JSON with the available interface paths.

## 4. Access each interface

### Admin interface

```text
http://localhost:8000/admin
```

Use it to:

- Check API health.
- View active sessions, participants, messages and traces.
- Select a session.
- Open participant or replay links.
- Preview report and transcript.
- View safe/masked configuration values.

Important note: `ADMIN_PASSWORD` exists in configuration, but this pilot version does **not** enforce login yet. Do not expose this app publicly before adding authentication.

### Facilitator interface

```text
http://localhost:8000/facilitator
```

Use it to:

1. Create a new session.
2. Copy the session ID.
3. Copy the participant link.
4. Move the session through phases.
5. Trigger devil’s advocate challenge questions.
6. Save facilitator injections/prompts.
7. Monitor participants, messages, ideas and phase state.

Typical flow:

```text
/facilitator → fill parameters → Start session → Copy participant URL → Share with participants
```

### Participant interface

After creating a session from the facilitator page, open the generated link:

```text
http://localhost:8000/participant?session_id=YOUR_SESSION_ID
```

Participants can:

- Join using the session ID.
- Keep or edit their generated participant ID.
- Send ideas, risks, assumptions or KPIs.
- Use quick prompt buttons to structure their answers.

The participant ID is stored in the browser local storage, so the same browser keeps the same ID unless it is manually changed.

### Replay interface

```text
http://localhost:8000/replay?session_id=YOUR_SESSION_ID
```

Use it to:

- Load a session by ID.
- Replay message progression.
- Inspect phases.
- Review ideas and traces.

You can also open it from the admin or facilitator UI.

## 5. Facilitator parameters explained

| Parameter | Where | Meaning | Recommended use |
|---|---|---|---|
| `topic` | Facilitator start form | Main problem or workshop question | Write one clear problem statement. Example: “How can we improve production planning?” |
| `target_mode` | Facilitator start form | Purpose of the session | Use `exploration` for open discovery, `decision` when choosing between options, `risk_review` for premortem/risk analysis, `innovation` for new solution generation. |
| `expected_participants` | Facilitator start form | Planned number of people | Helps compare expected vs actual participation later. |
| `expected_duration_minutes` | Facilitator start form | Planned workshop duration | Use 30–90 minutes for most pilots. |
| `language` | Facilitator start form | Main discussion language | Choose `fr`, `en`, `ar`, or `mixed`. This is stored in config for future LLM behavior. |
| `anonymity` | Facilitator start form | How participant identity should be treated | Use `anonymous` for open brainstorming, `named` for accountability workshops, `hybrid` when some actions need ownership. |
| `phase` | Facilitator phase control | Current step of the workshop | Move progressively: clarification → ideation → evaluation → refinement → closed. |
| `content_type` | Facilitator injection form | Type of facilitator intervention | Use `prompt` for guidance, `question` for clarification, `instruction` for process control, `idea` for adding a candidate idea. |
| `content` | Facilitator injection form | Text saved as facilitator intervention | Use short, direct messages that participants can act on. |

## 6. Admin parameters and controls explained

| Control | Meaning | How to use |
|---|---|---|
| Session list | Recent sessions saved in SQLite | Click one session to load its details. |
| Manual session ID | Direct session lookup | Paste a known session ID, then click `Load`. |
| Open participant link | Opens `/participant?session_id=...` | Use it to test the participant view. |
| Open replay | Opens `/replay?session_id=...` | Use it after or during a workshop to inspect progression. |
| Copy session ID | Copies only the raw ID | Useful for sharing with other screens or API calls. |
| Safe configuration view | Shows `.env` configuration with secrets masked | Use it to verify that dev/proto/pilot settings and API keys are detected. |

## 7. Environment variables explained

These values are read from `.env`.

| Variable | Meaning | Notes |
|---|---|---|
| `OPENROUTER_API_KEY` | API key for OpenRouter LLM calls | Optional for UI-only testing. |
| `GOOGLE_AI_API_KEY` | API key for Google AI/Gemini | Optional for UI-only testing. |
| `GROQ_API_KEY` / `GROK_API_KEY` | API key alias for Groq/Grok clients | The config normalizes `GROK_API_KEY` into `groq_api_key` if needed. |
| `ANTHROPIC_API_KEY` | API key for Anthropic | Optional for UI-only testing. |
| `ADMIN_PASSWORD` | Planned admin password | Currently not enforced by login middleware. |
| `FACILITATOR_PASSWORD` | Planned facilitator password | Currently not enforced by login middleware. |
| `MAX_USERS` | Maximum expected users | Used as configuration; not yet enforced hard in the UI. |
| `DEV_MODE` | Development mode flag | Keep `True` locally. |
| `PROTO_MODE` | Prototype mode flag | Keep `True` for pilot tests. |
| `PILOT_MODE` | Pilot mode flag | Keep `True` while testing incomplete features. |
| `LOG_LEVEL` | Logging verbosity | Use `DEBUG` while developing, `INFO` for cleaner logs. |

## 8. Recommended pilot workflow

1. Start the app with `uvicorn cip.main:app --reload`.
2. Open `/facilitator`.
3. Fill the topic and parameters.
4. Click **Start session**.
5. Copy the participant URL and share it with users.
6. Ask users to submit problem statements, ideas, risks and KPIs.
7. Use phase control to move from clarification to ideation, then evaluation and refinement.
8. Use devil’s advocate when the group converges too quickly.
9. Open `/admin` to monitor messages and traces.
10. Open `/replay?session_id=...` to review the session timeline.

## 9. Known limitations

This is still a pilot app. The UI is improved and the minimal session/message flow works, but the advanced collective-intelligence logic is not fully implemented yet.

Current limitations:

- No real login/authentication is enforced yet.
- LLM-based agents are still mostly stubs in the original project.
- Ideas/clusters are not automatically extracted from participant messages yet.
- Report generation is a compact JSON summary, not a final PDF report.
- WebSocket broadcast is session-aware for participant messages, but advanced moderation/broadcast features are still minimal.

## 10. Next recommended improvements

For the next version, prioritize:

1. Add login guards for `/admin` and `/facilitator`.
2. Add automatic idea extraction from messages.
3. Add cluster generation and visualization.
4. Add final report export as Markdown/PDF.
5. Add role-based permissions and session ownership.
6. Add better participant onboarding questions.
