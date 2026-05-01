#!/usr/bin/env python3
"""
CIP prototype EXTREME session simulator.

Purpose
-------
Simulates a full test session without needing 6 real human participants:
- optionally deletes the old SQLite database before the server starts,
- optionally starts the FastAPI/Uvicorn server,
- creates a new facilitator session,
- opens admin/facilitator WebSockets,
- opens 6 participant WebSockets,
- sends realistic participant messages,
- exercises facilitator actions: phase changes, devil advocate, injections,
- exercises admin APIs: telemetry, transcript, replay, traces, session logs, report,
- inspects SQLite tables and writes a Markdown + JSON report.

Recommended Windows usage from the project root:
    python scripts\simulate_proto_session.py --start-server --reset-db

Recommended Linux/Codespaces usage from the project root:
    python scripts/simulate_proto_session.py --start-server --reset-db

If your server is already running, do NOT use --reset-db. Use:
    python scripts/simulate_proto_session.py --base-url http://127.0.0.1:8000
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import signal
import sqlite3
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, urlunparse

import httpx
import websockets


# ----------------------------- helpers -----------------------------


def utc_now() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def to_ws_url(base_url: str, path: str) -> str:
    parsed = urlparse(base_url)
    scheme = "wss" if parsed.scheme == "https" else "ws"
    return urlunparse((scheme, parsed.netloc, path, "", "", ""))


def short_json(value: Any, max_len: int = 900) -> str:
    try:
        text = json.dumps(value, ensure_ascii=False, indent=2, default=str)
    except Exception:
        text = str(value)
    if len(text) > max_len:
        return text[:max_len] + f"... <truncated {len(text) - max_len} chars>"
    return text


@dataclass
class CheckResult:
    feature: str
    ok: bool
    detail: str = ""
    expected: bool = True
    data: Any = None


@dataclass
class Recorder:
    checks: list[CheckResult] = field(default_factory=list)

    def add(self, feature: str, ok: bool, detail: str = "", expected: bool = True, data: Any = None) -> None:
        self.checks.append(CheckResult(feature=feature, ok=ok, detail=detail, expected=expected, data=data))
        status = "OK" if ok else "FAIL"
        print(f"[{status}] {feature} - {detail}")

    def ok_count(self) -> int:
        return sum(1 for c in self.checks if c.ok)

    def fail_count(self) -> int:
        return sum(1 for c in self.checks if not c.ok)


# ----------------------------- database reset/inspection -----------------------------


def reset_sqlite_database(db_path: Path) -> None:
    """Delete cip.sqlite3 and sidecar files before the app starts."""
    for candidate in [db_path, Path(str(db_path) + "-wal"), Path(str(db_path) + "-shm")]:
        if candidate.exists():
            candidate.unlink()
            print(f"Deleted old database file: {candidate}")


def inspect_db(db_path: Path, session_id: str | None = None) -> dict[str, Any]:
    if not db_path.exists():
        return {"db_path": str(db_path), "exists": False, "error": "Database file does not exist"}

    result: dict[str, Any] = {"db_path": str(db_path), "exists": True, "tables": {}, "session": {}}
    tables = [
        "sessions",
        "participants",
        "messages",
        "events",
        "traces",
        "ideas",
        "clusters",
        "injections",
        "session_logs",
        "llm_cache",
        "session_configs",
    ]
    with sqlite3.connect(db_path) as con:
        con.row_factory = sqlite3.Row
        for table in tables:
            try:
                row = con.execute(f"SELECT COUNT(*) AS count FROM {table}").fetchone()
                result["tables"][table] = int(row["count"] if row else 0)
            except sqlite3.Error as exc:
                result["tables"][table] = f"missing/error: {exc}"

        if session_id:
            def count_where(table: str) -> int:
                row = con.execute(f"SELECT COUNT(*) AS count FROM {table} WHERE session_id = ?", (session_id,)).fetchone()
                return int(row["count"] if row else 0)

            for table in ["participants", "messages", "events", "traces", "ideas", "clusters", "injections", "session_logs"]:
                try:
                    result["session"][table] = count_where(table)
                except sqlite3.Error as exc:
                    result["session"][table] = f"missing/error: {exc}"

            try:
                result["session"]["warnings"] = int(
                    con.execute(
                        "SELECT COUNT(*) AS count FROM session_logs WHERE session_id = ? AND level = 'WARNING'",
                        (session_id,),
                    ).fetchone()["count"]
                )
                result["session"]["errors"] = int(
                    con.execute(
                        "SELECT COUNT(*) AS count FROM session_logs WHERE session_id = ? AND level = 'ERROR'",
                        (session_id,),
                    ).fetchone()["count"]
                )
                recent_logs = con.execute(
                    """
                    SELECT created_at, level, action, actor, status, message
                    FROM session_logs
                    WHERE session_id = ?
                    ORDER BY id DESC
                    LIMIT 15
                    """,
                    (session_id,),
                ).fetchall()
                result["session"]["recent_logs"] = [dict(row) for row in recent_logs]
            except sqlite3.Error as exc:
                result["session"]["log_summary_error"] = str(exc)
    return result


# ----------------------------- server management -----------------------------


async def wait_for_health(base_url: str, timeout_seconds: int, recorder: Recorder) -> bool:
    deadline = time.time() + timeout_seconds
    last_error = ""
    async with httpx.AsyncClient(timeout=3.0) as client:
        while time.time() < deadline:
            try:
                response = await client.get(f"{base_url}/health")
                if response.status_code == 200:
                    data = response.json()
                    recorder.add(
                        "health endpoint",
                        True,
                        f"server is ready; proto_logging_enabled={data.get('proto_logging_enabled')}",
                        data=data,
                    )
                    return True
                last_error = f"HTTP {response.status_code}: {response.text[:200]}"
            except Exception as exc:
                last_error = str(exc)
            await asyncio.sleep(0.5)
    recorder.add("health endpoint", False, f"server did not become ready: {last_error}")
    return False


def start_uvicorn_server(project_root: Path, host: str, port: int, env: dict[str, str]) -> subprocess.Popen:
    log_file = project_root / "simulation_server.log"
    log_handle = open(log_file, "w", encoding="utf-8")
    cmd = [sys.executable, "-m", "uvicorn", "cip.main:app", "--host", host, "--port", str(port)]
    print(f"Starting server: {' '.join(cmd)}")
    print(f"Server log file: {log_file}")
    return subprocess.Popen(
        cmd,
        cwd=str(project_root),
        env=env,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        text=True,
    )


def stop_process(process: subprocess.Popen | None) -> None:
    if process is None:
        return
    if process.poll() is not None:
        return
    print("Stopping local Uvicorn server...")
    try:
        process.terminate()
        process.wait(timeout=8)
    except Exception:
        try:
            process.kill()
        except Exception:
            pass


# ----------------------------- API/websocket tests -----------------------------


async def get_json(client: httpx.AsyncClient, recorder: Recorder, name: str, url: str, params: dict[str, Any] | None = None, expected_status: int = 200) -> dict[str, Any] | None:
    try:
        response = await client.get(url, params=params)
        ok = response.status_code == expected_status
        text = response.text[:300]
        data = None
        try:
            data = response.json()
        except Exception:
            pass
        recorder.add(name, ok, f"HTTP {response.status_code}; expected {expected_status}; {text}", data=data)
        return data if ok and isinstance(data, dict) else None
    except Exception as exc:
        recorder.add(name, False, f"exception: {exc}")
        return None


async def post_json(
    client: httpx.AsyncClient,
    recorder: Recorder,
    name: str,
    url: str,
    json_body: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
    expected_status: int = 200,
) -> dict[str, Any] | None:
    try:
        response = await client.post(url, json=json_body, params=params)
        ok = response.status_code == expected_status
        text = response.text[:300]
        data = None
        try:
            data = response.json()
        except Exception:
            pass
        recorder.add(name, ok, f"HTTP {response.status_code}; expected {expected_status}; {text}", data=data)
        return data if ok and isinstance(data, dict) else None
    except Exception as exc:
        recorder.add(name, False, f"exception: {exc}")
        return None


async def test_role_websocket(base_url: str, role: str, recorder: Recorder) -> None:
    """Check role websocket acceptance without requiring an echo frame."""
    ws_url = to_ws_url(base_url, f"/ws/{role}")
    try:
        async with websockets.connect(ws_url, open_timeout=8) as ws:
            await ws.send(json.dumps({"type": "ping", "role": role, "ts": utc_now()}))
            try:
                reply = await asyncio.wait_for(ws.recv(), timeout=2)
                recorder.add(f"{role} websocket", True, f"connected; received frame: {reply[:160]}")
            except asyncio.TimeoutError:
                recorder.add(f"{role} websocket", True, "connected; no immediate echo frame received, continuing behavior simulation", expected=False)
    except Exception as exc:
        recorder.add(f"{role} websocket", False, f"exception: {exc}")


PARTICIPANT_SCRIPTS: dict[str, list[str]] = {
    "P01_PRO": [
        "I strongly support the 4-day work week. It could increase motivation, reduce burnout, and force us to prioritize better.",
        "My vote: yes, but only if each team defines clear weekly outputs and owners.",
        "Concrete proposal: start with a 6-week pilot, measure productivity, absenteeism, employee satisfaction, and customer response time.",
        "Decision suggestion: approve a controlled pilot now instead of debating forever.",
    ],
    "P02_AGAINST": [
        "I strongly disagree. Same salary for fewer days may reduce service availability and create pressure on the remaining days.",
        "Clients will not care about our internal experiment if support becomes slower.",
        "Risk: hidden overtime. People may work evenings to compensate, then the policy becomes fake well-being.",
        "My condition: no adoption unless SLA and delivery quality stay stable for at least 2 months.",
    ],
    "P03_SKEPTIC": [
        "I am not against it, but I do not trust opinions. We need baseline data before the experiment.",
        "What exactly means productivity here: tasks closed, revenue, customer satisfaction, or team energy?",
        "We should define success and failure thresholds before launching the pilot.",
        "If metrics are ambiguous, everyone will interpret the result according to their preference.",
    ],
    "P04_OPERATIONS": [
        "Operational issue: meetings, handovers, and urgent requests must be redesigned before reducing working days.",
        "We need core availability windows and backup owners for every critical topic.",
        "A shared board with daily priorities could make the 4-day week possible.",
        "I propose rotating coverage: not everyone takes the same day off.",
    ],
    "P05_HR_WELLBEING": [
        "From a people perspective, this could improve retention and make recruitment easier.",
        "But managers must avoid compressing five days of meetings into four days.",
        "We should protect deep work blocks and remove low-value meetings first.",
        "Employee feedback must be anonymous because people may fear criticizing the pilot.",
    ],
    "P06_NOISY_EDGE": [
        "URGENT!!! We need action now, not another committee. Also this reminds me of remote work, AI tools, office coffee, and parking.",
        "Same point again: reduce meetings reduce meetings reduce meetings reduce meetings.",
        "   ",
        "This is a very long participant message meant to test logging and UI wrapping. " + "The system should keep the message readable, persist it correctly, and not break the transcript. " * 12,
    ],
}

EXTRA_HTTP_MESSAGES: list[dict[str, str]] = [
    {"participant_id": "P_HTTP_EMPTY", "text": ""},
    {"participant_id": "P_HTTP_DUP", "text": "Duplicate idea: define owners before work starts."},
    {"participant_id": "P_HTTP_DUP", "text": "Duplicate idea: define owners before work starts."},
    {"participant_id": "P_HTTP_FR", "text": "Je suis contre une adoption directe: il faut d'abord un pilote mesurable avec KPI clairs."},
    {"participant_id": "P_HTTP_AR", "text": "خاصنا نجربو الفكرة لمدة قصيرة ونقيسو النتائج قبل القرار النهائي."},
]

INJECTION_SCENARIOS: list[dict[str, str]] = [
    {"content_type": "question", "content": "Are you for or against the 4-day work week? Give one reason only."},
    {"content_type": "constraint", "content": "Assume customer response time must not increase by more than 5%."},
    {"content_type": "facilitator_prompt", "content": "Converge toward 3 concrete actions with owner, KPI, and deadline."},
    {"content_type": "risk", "content": "List the biggest failure mode after 3 months of deployment."},
    {"content_type": "summary", "content": "Summarize the strongest arguments for, against, and conditional adoption."},
]


async def wait_for_connected_frame(ws: Any, participant_id: str, timeout: float = 5.0) -> tuple[bool, str, int]:
    """Read frames until the participant receives its Connected frame."""
    deadline = time.time() + timeout
    frames_seen = 0
    last_frame = ""
    while time.time() < deadline:
        try:
            raw = await asyncio.wait_for(ws.recv(), timeout=max(0.2, deadline - time.time()))
        except asyncio.TimeoutError:
            break
        frames_seen += 1
        last_frame = str(raw)
        if "Connected" in last_frame:
            return True, last_frame, frames_seen
    return False, last_frame, frames_seen


async def simulate_participant(
    base_url: str,
    session_id: str,
    participant_id: str,
    messages: list[str],
    recorder: Recorder,
    rounds: int = 1,
    delay: float = 0.12,
) -> None:
    ws_url = to_ws_url(base_url, f"/ws/{session_id}/{participant_id}")
    received_count = 0
    sent_non_empty = 0
    sent_empty = 0
    try:
        async with websockets.connect(ws_url, open_timeout=8, ping_interval=20) as ws:
            connected, first, frames_seen = await wait_for_connected_frame(ws, participant_id)
            received_count += max(0, frames_seen - 1)
            recorder.add(
                f"participant {participant_id} websocket connect",
                connected,
                f"connected_frame={connected}; frames_seen_before_connected={frames_seen}; last_or_first={first[:160]}",
            )

            async def receiver() -> None:
                nonlocal received_count
                try:
                    async for _raw in ws:
                        received_count += 1
                except Exception:
                    pass

            receiver_task = asyncio.create_task(receiver())

            if participant_id.endswith("NOISY_EDGE"):
                await ws.send(json.dumps({"text": ""}))
                sent_empty += 1
                await asyncio.sleep(delay)

            for round_index in range(rounds):
                for msg_index, msg in enumerate(messages):
                    payload = {
                        "text": msg,
                        "client_ts": utc_now(),
                        "participant_id": participant_id,
                        "round": round_index + 1,
                        "message_index": msg_index + 1,
                        "stress_mode": "extreme_participant_behavior",
                    }
                    await ws.send(json.dumps(payload, ensure_ascii=False))
                    if msg.strip():
                        sent_non_empty += 1
                    else:
                        sent_empty += 1
                    await asyncio.sleep(delay)

            await asyncio.sleep(1.0)
            receiver_task.cancel()
            recorder.add(
                f"participant {participant_id} message send",
                True,
                f"sent_non_empty={sent_non_empty}; sent_empty={sent_empty}; received approx {received_count} broadcast frames",
            )
    except Exception as exc:
        recorder.add(f"participant {participant_id} websocket/session", False, f"exception: {exc}")


async def run_simulation(args: argparse.Namespace) -> dict[str, Any]:
    recorder = Recorder()
    base_url = args.base_url.rstrip("/")
    db_path = Path(args.db_path).resolve()
    run_id = f"sim-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
    session_id: str | None = None

    # Pages expected to exist.
    page_paths = ["/", "/admin", "/facilitator", "/participant", "/replay"]

    async with httpx.AsyncClient(timeout=httpx.Timeout(20.0, connect=8.0)) as client:
        ready = await wait_for_health(base_url, args.health_timeout, recorder)
        if not ready:
            return {"run_id": run_id, "session_id": None, "checks": [c.__dict__ for c in recorder.checks]}

        config = await get_json(client, recorder, "admin config", f"{base_url}/admin/api/config")
        if config:
            recorder.add(
                "proto logging configuration",
                bool(config.get("proto_logging_active")),
                f"proto_logging_active={config.get('proto_logging_active')}; proto_mode={config.get('proto_mode')}; proto_verbose_logging={config.get('proto_verbose_logging')}",
                data=config,
            )

        for path in page_paths:
            try:
                response = await client.get(f"{base_url}{path}")
                recorder.add(f"page {path}", response.status_code == 200, f"HTTP {response.status_code}")
            except Exception as exc:
                recorder.add(f"page {path}", False, f"exception: {exc}")

        start_payload = {
            "topic": args.topic,
            "language": "en/fr",
            "max_participants": 6,
            "simulation_run_id": run_id,
            "enable_proto_logging": True,
            "test_features": ["websocket", "phase", "devil", "inject", "admin_api", "replay", "sqlite_logs"],
        }
        start_data = await post_json(
            client,
            recorder,
            "facilitator start session",
            f"{base_url}/facilitator/api/session/start",
            json_body=start_payload,
        )
        if not start_data or not start_data.get("session_id"):
            recorder.add("simulation stopped", False, "could not create session")
            return {"run_id": run_id, "session_id": None, "checks": [c.__dict__ for c in recorder.checks]}
        session_id = str(start_data["session_id"])
        recorder.add("session id captured", True, session_id)

        # Role WebSockets: admin and facilitator.
        await asyncio.gather(
            test_role_websocket(base_url, "admin", recorder),
            test_role_websocket(base_url, "facilitator", recorder),
        )

        # Initial state.
        await get_json(client, recorder, "facilitator initial state", f"{base_url}/facilitator/api/session/state", params={"session_id": session_id})

        # Simulate 6 live participants.
        await asyncio.gather(
            *[
                simulate_participant(base_url, session_id, pid, msgs, recorder, rounds=args.extreme_rounds, delay=args.participant_delay)
                for pid, msgs in PARTICIPANT_SCRIPTS.items()
            ]
        )

        # HTTP fallback messages: empty, duplicate, multilingual and edge cases.
        for i, payload in enumerate(EXTRA_HTTP_MESSAGES, start=1):
            await post_json(
                client,
                recorder,
                f"HTTP fallback participant message {i}",
                f"{base_url}/api/session/{session_id}/message",
                json_body=payload,
                expected_status=200,
            )

        # Facilitator features: trigger every known phase button, devil advocate, and multiple injection types.
        phase_sequence = ["clarification", "ideation", "evaluation", "refinement", "ideation", "evaluation", "refinement"]
        for phase in phase_sequence:
            await post_json(
                client,
                recorder,
                f"facilitator phase change to {phase}",
                f"{base_url}/facilitator/api/session/phase",
                params={"session_id": session_id, "phase": phase},
            )
            await get_json(client, recorder, f"facilitator state after {phase}", f"{base_url}/facilitator/api/session/state", params={"session_id": session_id})

        await post_json(
            client,
            recorder,
            "facilitator invalid phase should fail",
            f"{base_url}/facilitator/api/session/phase",
            params={"session_id": session_id, "phase": "invalid_phase"},
            expected_status=400,
        )

        for phase in ["clarification", "ideation", "evaluation", "refinement"]:
            await post_json(
                client,
                recorder,
                f"facilitator devil advocate in {phase}",
                f"{base_url}/facilitator/api/session/devil",
                params={"session_id": session_id, "phase": phase},
            )

        for i, injection in enumerate(INJECTION_SCENARIOS, start=1):
            await post_json(
                client,
                recorder,
                f"facilitator content injection {i} ({injection['content_type']})",
                f"{base_url}/facilitator/api/session/inject",
                params={"session_id": session_id, **injection},
            )

        await post_json(
            client,
            recorder,
            "facilitator empty injection should fail",
            f"{base_url}/facilitator/api/session/inject",
            params={"session_id": session_id, "content_type": "prompt", "content": "   "},
            expected_status=400,
        )

        # Admin APIs.
        await get_json(client, recorder, "admin sessions", f"{base_url}/admin/api/sessions", params={"limit": 10})
        telemetry = await get_json(client, recorder, "admin telemetry", f"{base_url}/admin/api/telemetry")
        transcript = await get_json(client, recorder, "admin transcript", f"{base_url}/admin/api/transcript", params={"session_id": session_id})
        replay = await get_json(client, recorder, "admin replay data", f"{base_url}/admin/api/replay", params={"session_id": session_id})
        traces = await get_json(client, recorder, "admin traces", f"{base_url}/admin/api/traces", params={"session_id": session_id, "limit": 50})
        logs = await get_json(client, recorder, "admin session logs", f"{base_url}/admin/api/session-logs", params={"session_id": session_id, "limit": 500})
        warnings = await get_json(client, recorder, "admin session warnings", f"{base_url}/admin/api/session-logs", params={"session_id": session_id, "level": "WARNING", "limit": 100})
        report = await get_json(client, recorder, "admin report", f"{base_url}/admin/api/report", params={"session_id": session_id})

        # Feature-level assertions from returned data.
        expected_messages = sum(len(v) for v in PARTICIPANT_SCRIPTS.values()) * args.extreme_rounds + sum(1 for m in EXTRA_HTTP_MESSAGES if m["text"].strip())
        if transcript:
            count = int(transcript.get("count", 0))
            recorder.add("transcript message count", count >= expected_messages, f"count={count}; expected >= {expected_messages}", data=transcript)
        if report:
            recorder.add("report participant count", int(report.get("participants_count", 0)) >= 6, f"participants_count={report.get('participants_count')}", data=report)
            recorder.add("report message count", int(report.get("messages_count", 0)) >= expected_messages, f"messages_count={report.get('messages_count')}", data=report)
            recorder.add("report injection count", len(report.get("recent_injections") or []) >= 2, f"recent_injections={len(report.get('recent_injections') or [])}", data=report)
        if logs:
            recorder.add("proto logs count", int(logs.get("count", 0)) > 0, f"logs_count={logs.get('count')}", data=logs)
        if warnings:
            recorder.add("expected warning logs", int(warnings.get("count", 0)) >= 1, f"warning_count={warnings.get('count')}", data=warnings)
        if telemetry:
            recorder.add("telemetry proto logs visible", int(telemetry.get("total_proto_logs", 0)) > 0, f"total_proto_logs={telemetry.get('total_proto_logs')}", data=telemetry)
        if traces:
            recorder.add("trace rows visible", int(traces.get("count", 0)) > 0, f"traces_count={traces.get('count')}", data=traces)
        if replay:
            recorder.add("replay includes logs", len(replay.get("logs") or []) > 0, f"logs_in_replay={len(replay.get('logs') or [])}", data=replay)

        # Close the session at the end.
        await post_json(
            client,
            recorder,
            "facilitator close session",
            f"{base_url}/facilitator/api/session/phase",
            params={"session_id": session_id, "phase": "closed"},
        )

    db_summary = inspect_db(db_path, session_id)
    if db_summary.get("exists"):
        s = db_summary.get("session", {})
        recorder.add("sqlite session participants persisted", int(s.get("participants", 0) or 0) >= 6, f"participants={s.get('participants')}", data=s)
        recorder.add("sqlite session messages persisted", int(s.get("messages", 0) or 0) >= 19, f"messages={s.get('messages')}", data=s)
        recorder.add("sqlite session logs persisted", int(s.get("session_logs", 0) or 0) > 0, f"session_logs={s.get('session_logs')}", data=s)
        recorder.add("sqlite traces persisted", int(s.get("traces", 0) or 0) > 0, f"traces={s.get('traces')}", data=s)
    else:
        recorder.add("sqlite database exists", False, str(db_summary))

    # Expected current limitation: no AI ideas/clusters unless a separate extractor/orchestrator is triggered.
    if db_summary.get("exists"):
        s = db_summary.get("session", {})
        ideas_count = int(s.get("ideas", 0) or 0)
        clusters_count = int(s.get("clusters", 0) or 0)
        recorder.add(
            "AI idea extraction automatically triggered",
            ideas_count > 0,
            f"ideas={ideas_count}; if 0, messages are saved but not analyzed automatically",
            expected=False,
        )
        recorder.add(
            "AI clustering automatically triggered",
            clusters_count > 0,
            f"clusters={clusters_count}; if 0, clustering is not triggered automatically",
            expected=False,
        )

    return {
        "run_id": run_id,
        "base_url": base_url,
        "session_id": session_id,
        "generated_at": utc_now(),
        "summary": {"ok": recorder.ok_count(), "failed": recorder.fail_count()},
        "checks": [c.__dict__ for c in recorder.checks],
        "db_summary": db_summary,
    }


# ----------------------------- report -----------------------------


def write_reports(project_root: Path, report: dict[str, Any]) -> tuple[Path, Path]:
    session_id = report.get("session_id") or "no-session"
    ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    json_path = project_root / f"simulation_report_{ts}.json"
    md_path = project_root / f"simulation_report_{ts}.md"

    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    checks = report.get("checks", [])
    failed = [c for c in checks if not c.get("ok")]
    working = [c for c in checks if c.get("ok")]
    db_summary = report.get("db_summary", {})
    session_db = db_summary.get("session", {}) if isinstance(db_summary, dict) else {}

    md_lines = [
        f"# CIP Simulation Report",
        "",
        f"- Generated at: `{report.get('generated_at')}`",
        f"- Run ID: `{report.get('run_id')}`",
        f"- Base URL: `{report.get('base_url')}`",
        f"- Session ID: `{session_id}`",
        f"- Checks OK: `{report.get('summary', {}).get('ok')}`",
        f"- Checks failed/limited: `{report.get('summary', {}).get('failed')}`",
        "",
        "## Database summary for this session",
        "",
        "| Table / metric | Count |",
        "|---|---:|",
    ]
    for key, value in session_db.items():
        if key == "recent_logs":
            continue
        md_lines.append(f"| `{key}` | `{value}` |")

    md_lines.extend([
        "",
        "## What works",
        "",
    ])
    for c in working:
        md_lines.append(f"- ✅ **{c.get('feature')}** — {c.get('detail')}")

    md_lines.extend([
        "",
        "## What failed or is not triggered automatically",
        "",
    ])
    if not failed:
        md_lines.append("No failed checks.")
    else:
        for c in failed:
            expected_note = " _(expected limitation)_" if c.get("expected") is False else ""
            md_lines.append(f"- ❌ **{c.get('feature')}**{expected_note} — {c.get('detail')}")

    recent_logs = session_db.get("recent_logs") or []
    md_lines.extend([
        "",
        "## Recent proto logs",
        "",
    ])
    if recent_logs:
        md_lines.append("| Time | Level | Actor | Action | Status | Message |")
        md_lines.append("|---|---|---|---|---|---|")
        for row in recent_logs:
            md_lines.append(
                f"| {row.get('created_at')} | {row.get('level')} | {row.get('actor')} | {row.get('action')} | {row.get('status')} | {str(row.get('message', '')).replace('|', '/')} |"
            )
    else:
        md_lines.append("No recent proto logs found.")

    md_lines.extend([
        "",
        "## Interpretation",
        "",
        "If `messages`, `events`, `session_logs`, and `traces` are greater than zero, the live session and prototype logging are working.",
        "If `ideas` and `clusters` are zero, the app is saving conversation data but the AI extraction/clustering pipeline is not being triggered automatically by participant messages.",
    ])

    md_path.write_text("\n".join(md_lines), encoding="utf-8")
    return md_path, json_path


# ----------------------------- main -----------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extreme CIP behavior simulation with 6 participants and all known facilitator/admin controls.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Base URL of the CIP app.")
    parser.add_argument("--host", default="127.0.0.1", help="Host used when --start-server is enabled.")
    parser.add_argument("--port", type=int, default=8000, help="Port used when --start-server is enabled.")
    parser.add_argument("--start-server", action="store_true", help="Start Uvicorn from this script.")
    parser.add_argument("--reset-db", action="store_true", help="Delete cip.sqlite3 before starting the server. Only safe with --start-server.")
    parser.add_argument("--db-path", default="cip.sqlite3", help="SQLite database path relative to project root or absolute.")
    parser.add_argument("--health-timeout", type=int, default=30, help="Seconds to wait for server readiness.")
    parser.add_argument("--topic", default="Should our company adopt a 4-day work week while keeping the same salary?", help="Topic used for the simulated session.")
    parser.add_argument("--extreme-rounds", type=int, default=2, help="How many participant message rounds to run.")
    parser.add_argument("--participant-delay", type=float, default=0.12, help="Delay between participant messages.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_root = Path.cwd().resolve()
    db_path = Path(args.db_path)
    if not db_path.is_absolute():
        db_path = project_root / db_path

    server_process: subprocess.Popen | None = None

    if args.reset_db and not args.start_server:
        print("ERROR: --reset-db is only safe when used with --start-server.")
        print("Stop your server first, then run: python scripts/simulate_proto_session.py --start-server --reset-db")
        return 2

    try:
        if args.reset_db:
            reset_sqlite_database(db_path)

        if args.start_server:
            env = os.environ.copy()
            # Force proto logging for the child server during this simulation only.
            env["PROTO_MODE"] = "True"
            env["PROTO_VERBOSE_LOGGING"] = "True"
            env["PROTO_LOG_TO_CONSOLE"] = "True"
            env["LOG_LEVEL"] = "DEBUG"
            server_process = start_uvicorn_server(project_root, args.host, args.port, env)
            args.base_url = f"http://{args.host}:{args.port}"

        report = asyncio.run(run_simulation(args))
        md_path, json_path = write_reports(project_root, report)
        print("\nSimulation finished.")
        print(f"Markdown report: {md_path}")
        print(f"JSON report:     {json_path}")
        print(f"Session ID:      {report.get('session_id')}")
        print(f"Summary:         {report.get('summary')}")
        return 0 if report.get("summary", {}).get("failed", 1) == 0 else 1
    finally:
        stop_process(server_process)


if __name__ == "__main__":
    raise SystemExit(main())
