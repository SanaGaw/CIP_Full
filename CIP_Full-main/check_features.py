#!/usr/bin/env python3
"""
CIP v2.0 — Feature audit script.

Usage:
    python check_features.py

Run this from the repo root. It probes the codebase to determine which
features are real, partial, or stubbed. Output is a CHECK_REPORT.md file
which you paste into the chat with Claude when asking for next steps.

Token-efficient: produces a compact pass/fail report Claude can parse quickly.
"""
from __future__ import annotations

import ast
import asyncio
import importlib
import inspect
import json
import os
import re
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
REPORT = ROOT / "CHECK_REPORT.md"

results: list[dict] = []


def record(category: str, name: str, status: str, evidence: str = "") -> None:
    """status: PASS | FAIL | STUB | SKIP"""
    results.append({"category": category, "name": name, "status": status, "evidence": evidence[:200]})


def file_text(rel: str) -> str:
    p = ROOT / rel
    if not p.exists():
        return ""
    return p.read_text(encoding="utf-8", errors="ignore")


def has_pattern(rel: str, pattern: str) -> bool:
    return bool(re.search(pattern, file_text(rel), re.IGNORECASE | re.DOTALL))


def is_stub(rel: str) -> tuple[bool, str]:
    """Detects stub markers in a file."""
    txt = file_text(rel)
    if not txt:
        return True, "file missing"
    markers = [
        (r"\bstub\b", "contains the word 'stub'"),
        (r"placeholder", "contains 'placeholder'"),
        (r"TODO:?\s*implement", "contains 'TODO: implement'"),
        (r"# TODO", "contains '# TODO'"),
        (r"raise NotImplementedError", "raises NotImplementedError"),
        (r"return\s*\{\s*\}\s*$", "returns empty dict"),
        (r"return\s*\[\s*\]\s*$", "returns empty list"),
        (r"return\s+None\s*$", "returns None only"),
    ]
    for pat, msg in markers:
        if re.search(pat, txt, re.IGNORECASE | re.MULTILINE):
            return True, msg
    return False, ""


# ────────────────────────────────────────────────────────────────────
# CATEGORY 1: STRUCTURE
# ────────────────────────────────────────────────────────────────────
def check_structure() -> None:
    expected = [
        "cip/main.py", "cip/config.py", "cip/db.py", "cip/state.py", "cip/session.py",
        "cip/observability.py", "cip/metrics.py",
        "cip/agents/conversation.py", "cip/agents/orchestrator.py", "cip/agents/devil.py",
        "cip/agents/rapporteur.py", "cip/agents/problem_crystallizer.py",
        "cip/agents/hypothesis.py", "cip/agents/idea_extractor.py",
        "cip/engines/criteria.py", "cip/engines/condorcet.py", "cip/engines/bridging.py",
        "cip/engines/bias.py",
        "cip/nlp/embeddings.py", "cip/nlp/clustering.py", "cip/nlp/diversity.py",
        "cip/nlp/language.py",
        "cip/llm/clients.py", "cip/llm/tier_router.py", "cip/llm/tier_map.py",
        "cip/llm/cache.py",
        "cip/admin/routes.py", "cip/facilitator/routes.py",
        "cip/websocket/manager.py",
        "cip/templates/admin/dashboard.html",
        "cip/templates/facilitator/dashboard.html",
        "cip/templates/participant/chat.html",
        "cip/templates/replay/session.html",
        "requirements.txt", ".env.example", "Dockerfile", "Procfile", "railway.toml",
    ]
    for f in expected:
        if (ROOT / f).exists():
            record("STRUCTURE", f, "PASS")
        else:
            record("STRUCTURE", f, "FAIL", "file missing")


# ────────────────────────────────────────────────────────────────────
# CATEGORY 2: LLM CLIENTS — must make REAL HTTP calls
# ────────────────────────────────────────────────────────────────────
def check_llm_clients() -> None:
    txt = file_text("cip/llm/clients.py")
    providers = ["anthropic", "openrouter", "gemini", "groq"]
    for p in providers:
        # A real implementation should reference httpx/requests OR the official SDK
        has_http = bool(re.search(r"httpx|requests\.|aiohttp|client\.messages\.create|generativeai|groq\.", txt))
        has_stub = "stub response" in txt.lower() or f"[{p}] stub" in txt.lower()
        if has_stub and not has_http:
            record("LLM_CLIENT", f"call_{p}", "STUB", "returns stub response, no HTTP call")
        elif has_http:
            # Check this specific provider has real call
            pattern = rf"def call_{p}.*?(?=async def|def call_|\Z)"
            m = re.search(pattern, txt, re.DOTALL)
            if m and re.search(r"httpx|requests|aiohttp|messages\.create|GenerativeModel|Groq\(", m.group(0)):
                record("LLM_CLIENT", f"call_{p}", "PASS")
            else:
                record("LLM_CLIENT", f"call_{p}", "STUB", "no real HTTP call in this function")
        else:
            record("LLM_CLIENT", f"call_{p}", "FAIL", "function not found")


# ────────────────────────────────────────────────────────────────────
# CATEGORY 3: CORE AGENTS
# ────────────────────────────────────────────────────────────────────
def check_agents() -> None:
    # Conversation agent: 8 modes
    txt = file_text("cip/agents/conversation.py")
    modes = ["LISTEN", "NARRATE", "REFLECT", "BRIDGE", "RECALL", "PREMORTEM", "CRITERIA", "PAIRWISE"]
    for m in modes:
        # Detect if mode has its own handler that does more than return empty
        handler_pattern = rf"_{m.lower()}\s*\(.*?\).*?(?=async def|def |\Z)"
        match = re.search(handler_pattern, txt, re.DOTALL)
        if not match:
            # Check if at least it's referenced in handle()
            if re.search(rf"ConversationMode\.{m}", txt):
                record("AGENT_CONV", f"mode_{m}", "STUB", "referenced but no _handler implementation")
            else:
                record("AGENT_CONV", f"mode_{m}", "FAIL", "not implemented")
        else:
            body = match.group(0)
            if len(body) < 200 or 'return {"text": "", "profile_update": {}}' in body:
                record("AGENT_CONV", f"mode_{m}", "STUB", "handler is empty/skeleton")
            else:
                record("AGENT_CONV", f"mode_{m}", "PASS")
    # Profile update parsing
    if re.search(r"\[PROFILE_UPDATE\]", txt):
        record("AGENT_CONV", "profile_update_parsing", "PASS")
    else:
        record("AGENT_CONV", "profile_update_parsing", "FAIL", "no PROFILE_UPDATE block parsing")

    # Orchestrator: 8-step pipeline
    txt = file_text("cip/agents/orchestrator.py")
    pipeline_steps = [
        ("similarity_check", r"similarit"),
        ("dimension_assessment", r"dimension"),
        ("tension_check", r"tension"),
        ("mece_audit", r"mece|overlap"),
        ("hypothesis_evidence", r"hypothesis_evidence"),
        ("mab_routing", r"mab|bandit|epsilon"),
        ("minority_boost", r"minority"),
        ("perspective_gap", r"perspective_gap"),
    ]
    for name, pat in pipeline_steps:
        if re.search(pat, txt, re.IGNORECASE):
            record("AGENT_ORCH", name, "PASS")
        else:
            record("AGENT_ORCH", name, "FAIL", "step not found")
    # Bayesian
    if re.search(r"bayesian|posterior", txt, re.IGNORECASE):
        record("AGENT_ORCH", "bayesian_update", "PASS")
    else:
        record("AGENT_ORCH", "bayesian_update", "FAIL", "no Bayesian update")
    # Stagnation
    if re.search(r"stagnation", txt, re.IGNORECASE):
        record("AGENT_ORCH", "stagnation_detection", "PASS")
    else:
        record("AGENT_ORCH", "stagnation_detection", "FAIL", "no stagnation logic")

    # Devil
    txt = file_text("cip/agents/devil.py")
    frameworks = ["lateral_thinking", "blue_ocean", "scamper", "premortem"]
    found_frameworks = sum(1 for f in frameworks if f in txt.lower())
    if found_frameworks >= 3:
        record("AGENT_DEVIL", "phase_frameworks", "PASS", f"{found_frameworks}/4 frameworks")
    else:
        record("AGENT_DEVIL", "phase_frameworks", "STUB", f"only {found_frameworks}/4 frameworks referenced")
    if "stress_test" in txt.lower():
        record("AGENT_DEVIL", "stress_test", "PASS")
    else:
        record("AGENT_DEVIL", "stress_test", "FAIL", "no stress_test")
    stub, ev = is_stub("cip/agents/devil.py")
    if stub:
        record("AGENT_DEVIL", "implementation", "STUB", ev)
    else:
        record("AGENT_DEVIL", "implementation", "PASS")

    # Rapporteur — must have 11 sections
    txt = file_text("cip/agents/rapporteur.py")
    sections_needed = [
        "session_overview", "problem_statement", "hypothesis_trajectory",
        "idea_landscape", "key_tensions", "pluralism", "criteria_analysis",
        "option_ranking", "recommendation", "creative_disruption", "next_steps",
    ]
    found_sections = sum(1 for s in sections_needed if s.replace("_", " ") in txt.lower() or s in txt.lower())
    if found_sections >= 8:
        record("AGENT_RAP", "11_section_report", "PASS", f"{found_sections}/11 sections")
    elif found_sections >= 3:
        record("AGENT_RAP", "11_section_report", "STUB", f"only {found_sections}/11 sections")
    else:
        record("AGENT_RAP", "11_section_report", "FAIL", "no real report structure")
    if "report.json" in txt or '"json"' in txt or "json.dump" in txt:
        record("AGENT_RAP", "json_output", "PASS")
    else:
        record("AGENT_RAP", "json_output", "FAIL", "no json output")

    # Problem Crystallizer
    txt = file_text("cip/agents/problem_crystallizer.py")
    if "call_with_tier" in txt and "pc.synthesize" in txt:
        record("AGENT_PC", "uses_llm", "PASS")
    else:
        record("AGENT_PC", "uses_llm", "STUB", "doesn't actually call LLM")

    # Hypothesis
    txt = file_text("cip/agents/hypothesis.py")
    if "call_with_tier" in txt and "hyp.generate" in txt:
        record("AGENT_HYP", "uses_llm", "PASS")
    else:
        record("AGENT_HYP", "uses_llm", "STUB", "doesn't actually call LLM")


# ────────────────────────────────────────────────────────────────────
# CATEGORY 4: ENGINES
# ────────────────────────────────────────────────────────────────────
def check_engines() -> None:
    # Bridging — must have Bayesian override + anchoring
    txt = file_text("cip/engines/bridging.py")
    if "similarity_score = 0.5" in txt or "placeholder constant" in txt:
        record("ENGINE_BRIDGE", "real_similarity", "STUB", "uses placeholder constant 0.5")
    else:
        record("ENGINE_BRIDGE", "real_similarity", "PASS")
    if re.search(r"bayesian|posterior", txt, re.IGNORECASE):
        record("ENGINE_BRIDGE", "bayesian_override", "PASS")
    else:
        record("ENGINE_BRIDGE", "bayesian_override", "FAIL", "no Bayesian override")
    if "anchoring" in txt.lower():
        record("ENGINE_BRIDGE", "anchoring_detection", "PASS")
    else:
        record("ENGINE_BRIDGE", "anchoring_detection", "FAIL", "no anchoring")

    # Bias engine
    stub, ev = is_stub("cip/engines/bias.py")
    if stub:
        record("ENGINE_BIAS", "implementation", "STUB", ev)
    else:
        record("ENGINE_BIAS", "implementation", "PASS")

    # AHP — likely OK
    txt = file_text("cip/engines/criteria.py")
    if "consistency_ratio" in txt and "priority_vector" in txt:
        record("ENGINE_AHP", "core_math", "PASS")
    else:
        record("ENGINE_AHP", "core_math", "FAIL", "missing core AHP math")

    # Condorcet
    txt = file_text("cip/engines/condorcet.py")
    if "condorcet_winner" in txt and "borda" in txt.lower():
        record("ENGINE_CONDORCET", "core_logic", "PASS")
    else:
        record("ENGINE_CONDORCET", "core_logic", "FAIL")
    # Cycle detection — current impl is basic
    if re.search(r"def.*cycle|detect_cycle", txt) or "A>B" in txt:
        record("ENGINE_CONDORCET", "real_cycle_detection", "PASS")
    else:
        record("ENGINE_CONDORCET", "real_cycle_detection", "STUB", "naive cycle = no Condorcet winner")


# ────────────────────────────────────────────────────────────────────
# CATEGORY 5: NLP
# ────────────────────────────────────────────────────────────────────
def check_nlp() -> None:
    # Embeddings
    txt = file_text("cip/nlp/embeddings.py")
    if "SentenceTransformer" in txt and "all-MiniLM" in txt:
        record("NLP_EMBED", "model_loading", "PASS")
    else:
        record("NLP_EMBED", "model_loading", "FAIL")
    # Diversity — current impl is stub (uniform distribution)
    txt = file_text("cip/nlp/diversity.py")
    if "Real implementation" in txt or "Simple uniform" in txt:
        record("NLP_DIVERSITY", "implementation", "STUB", "assumes uniform distribution; ignores clustering")
    elif "shannon" in txt.lower() and "cluster" in txt.lower():
        record("NLP_DIVERSITY", "implementation", "PASS")
    else:
        record("NLP_DIVERSITY", "implementation", "STUB", "doesn't use real clusters")
    # Clustering
    txt = file_text("cip/nlp/clustering.py")
    if "AgglomerativeClustering" in txt:
        record("NLP_CLUSTER", "implementation", "PASS")
    else:
        record("NLP_CLUSTER", "implementation", "FAIL")


# ────────────────────────────────────────────────────────────────────
# CATEGORY 6: IDEA EXTRACTOR — quality scoring depth
# ────────────────────────────────────────────────────────────────────
def check_extractor() -> None:
    txt = file_text("cip/agents/idea_extractor.py")
    # extract_ideas: current impl is just sentence split
    if "spaCy" in txt or ("nsubj" in txt) or ("nlp(" in txt):
        record("EXTRACTOR", "spacy_analysis", "PASS")
    else:
        record("EXTRACTOR", "spacy_analysis", "STUB", "sentence-split only, no spaCy syntactic analysis")
    # quality scoring with all 5 dimensions actually computed
    if re.search(r"def\s+_?compute_specificity|specificity\s*=\s*[a-z_]+\(", txt):
        record("EXTRACTOR", "quality_specificity", "PASS")
    else:
        record("EXTRACTOR", "quality_specificity", "STUB", "specificity hardcoded")
    if re.search(r"_?evidence\s*=\s*[a-z_]+\(", txt) and "evidence = 0.5" not in txt:
        record("EXTRACTOR", "quality_evidence", "PASS")
    else:
        record("EXTRACTOR", "quality_evidence", "STUB", "evidence hardcoded to 0.5")
    if "novelty = 0.5" in txt or "relevance = 0.5" in txt:
        record("EXTRACTOR", "quality_novelty_relevance", "STUB", "hardcoded to 0.5")
    else:
        record("EXTRACTOR", "quality_novelty_relevance", "PASS")
    # narrative parsing — regex only is acceptable but check it's present
    if "NARRATIVE_PATTERNS" in txt and "parse_narrative_elements" in txt:
        record("EXTRACTOR", "narrative_parsing", "PASS")
    else:
        record("EXTRACTOR", "narrative_parsing", "FAIL")
    # bias detection
    if "BIAS_SIGNALS" in txt and "detect_biases" in txt:
        record("EXTRACTOR", "bias_signals", "PASS")
    else:
        record("EXTRACTOR", "bias_signals", "FAIL")


# ────────────────────────────────────────────────────────────────────
# CATEGORY 7: METRICS
# ────────────────────────────────────────────────────────────────────
def check_metrics() -> None:
    txt = file_text("cip/metrics.py")
    if "synthetic_ratio" in txt:
        # Check it actually computes from data
        if 'return {\n        "A": 0' in txt or "synthetic_ratio\": 0.0" in txt and len(txt) < 600:
            record("METRICS", "synthetic_idea_ratio", "STUB", "returns zeros, no real computation")
        elif re.search(r"async\s+with\s+get_db", txt):
            record("METRICS", "synthetic_idea_ratio", "PASS")
        else:
            record("METRICS", "synthetic_idea_ratio", "STUB", "no DB queries")
    else:
        record("METRICS", "synthetic_idea_ratio", "FAIL")
    if "died_unfairly" in txt:
        if "return []" in txt and len(txt.split("died_unfairly")[1]) < 300:
            record("METRICS", "died_unfairly", "STUB", "returns empty list")
        else:
            record("METRICS", "died_unfairly", "PASS")
    else:
        record("METRICS", "died_unfairly", "FAIL")


# ────────────────────────────────────────────────────────────────────
# CATEGORY 8: ROUTES
# ────────────────────────────────────────────────────────────────────
def check_routes() -> None:
    # Admin — should expose multiple endpoints
    txt = file_text("cip/admin/routes.py")
    endpoints = ["/admin/api/config", "/admin/api/telemetry", "/admin/api/traces",
                 "/admin/api/report", "/admin/api/transcript", "/admin/api/replay"]
    found = sum(1 for e in endpoints if e in txt)
    if found >= 4:
        record("ROUTES_ADMIN", "endpoints_coverage", "PASS", f"{found}/{len(endpoints)}")
    else:
        record("ROUTES_ADMIN", "endpoints_coverage", "STUB", f"only {found}/{len(endpoints)} endpoints")

    txt = file_text("cip/facilitator/routes.py")
    fac_endpoints = ["/facilitator/api/session/start", "/facilitator/api/session/phase",
                     "/facilitator/api/session/devil", "/facilitator/api/session/inject",
                     "/facilitator/api/session/state"]
    found = sum(1 for e in fac_endpoints if e in txt)
    if found >= 3:
        record("ROUTES_FAC", "endpoints_coverage", "PASS", f"{found}/{len(fac_endpoints)}")
    else:
        record("ROUTES_FAC", "endpoints_coverage", "STUB", f"only {found}/{len(fac_endpoints)} endpoints")


# ────────────────────────────────────────────────────────────────────
# CATEGORY 9: TEMPLATES
# ────────────────────────────────────────────────────────────────────
def check_templates() -> None:
    for name, path in [
        ("participant_chat", "cip/templates/participant/chat.html"),
        ("admin_dashboard", "cip/templates/admin/dashboard.html"),
        ("facilitator_dashboard", "cip/templates/facilitator/dashboard.html"),
        ("replay_session", "cip/templates/replay/session.html"),
    ]:
        txt = file_text(path)
        line_count = len(txt.splitlines())
        # A real template needs to be substantial
        has_logic = bool(re.search(r"WebSocket|fetch\(|onclick|@click|addEventListener", txt))
        if line_count > 50 and has_logic:
            record("TEMPLATE", name, "PASS")
        elif line_count > 50:
            record("TEMPLATE", name, "STUB", "no JS interactivity")
        else:
            record("TEMPLATE", name, "STUB", f"only {line_count} lines, skeleton")


# ────────────────────────────────────────────────────────────────────
# CATEGORY 10: APP CAN BOOT
# ────────────────────────────────────────────────────────────────────
def check_app_boots() -> None:
    """Try to import the FastAPI app without crashing."""
    sys.path.insert(0, str(ROOT))
    # Set required env vars to prevent Settings() from raising
    os.environ.setdefault("ADMIN_PASSWORD", "test")
    os.environ.setdefault("FACILITATOR_PASSWORD", "test")
    try:
        # Force-reload to pick up env
        if "cip" in sys.modules:
            for mod in list(sys.modules):
                if mod.startswith("cip"):
                    del sys.modules[mod]
        from cip.main import app  # noqa
        record("APP", "imports_cleanly", "PASS")
    except Exception as e:
        record("APP", "imports_cleanly", "FAIL", f"{type(e).__name__}: {e}")
        return

    # Check health endpoint exists
    try:
        from fastapi.testclient import TestClient
        client = TestClient(app)
        r = client.get("/health")
        if r.status_code == 200:
            record("APP", "health_endpoint", "PASS")
        else:
            record("APP", "health_endpoint", "FAIL", f"status {r.status_code}")
    except Exception as e:
        record("APP", "health_endpoint", "FAIL", str(e))


# ────────────────────────────────────────────────────────────────────
# CATEGORY 11: TESTS RUN
# ────────────────────────────────────────────────────────────────────
def check_tests_run() -> None:
    """Try running pytest on existing tests."""
    try:
        import subprocess
        result = subprocess.run(
            ["python", "-m", "pytest", "tests/", "-q", "--tb=no", "--no-header"],
            capture_output=True, text=True, cwd=str(ROOT), timeout=120,
        )
        # parse "X passed, Y failed"
        m = re.search(r"(\d+)\s+passed", result.stdout + result.stderr)
        f = re.search(r"(\d+)\s+failed", result.stdout + result.stderr)
        passed = int(m.group(1)) if m else 0
        failed = int(f.group(1)) if f else 0
        if failed == 0 and passed > 0:
            record("TESTS", "pytest_run", "PASS", f"{passed} passed, 0 failed")
        elif passed > 0:
            record("TESTS", "pytest_run", "STUB", f"{passed} passed, {failed} failed")
        else:
            record("TESTS", "pytest_run", "FAIL", f"no tests passed; output: {result.stdout[:150]}")
    except Exception as e:
        record("TESTS", "pytest_run", "FAIL", str(e))


# ────────────────────────────────────────────────────────────────────
# REPORT
# ────────────────────────────────────────────────────────────────────
def write_report() -> None:
    by_cat: dict[str, list[dict]] = {}
    for r in results:
        by_cat.setdefault(r["category"], []).append(r)

    total = len(results)
    passes = sum(1 for r in results if r["status"] == "PASS")
    stubs = sum(1 for r in results if r["status"] == "STUB")
    fails = sum(1 for r in results if r["status"] == "FAIL")

    lines = [
        f"# CIP v2.0 — Feature Audit Report",
        f"_Generated: {datetime.utcnow().isoformat()}Z_",
        "",
        f"## Summary",
        f"- Total checks: **{total}**",
        f"- ✅ PASS:  **{passes}**",
        f"- ⚠️ STUB:  **{stubs}**  (exists but not real)",
        f"- ❌ FAIL:  **{fails}**  (missing or broken)",
        f"- **Implementation completeness: {round(100*passes/total)}%**",
        "",
        "## Results by category",
        "",
    ]
    for cat in sorted(by_cat.keys()):
        items = by_cat[cat]
        cat_pass = sum(1 for i in items if i["status"] == "PASS")
        lines.append(f"### {cat}  ({cat_pass}/{len(items)})")
        lines.append("")
        lines.append("| Check | Status | Evidence |")
        lines.append("|---|---|---|")
        for i in items:
            icon = {"PASS": "✅", "STUB": "⚠️", "FAIL": "❌", "SKIP": "⏭️"}.get(i["status"], "?")
            ev = i["evidence"].replace("|", "\\|") if i["evidence"] else ""
            lines.append(f"| {i['name']} | {icon} {i['status']} | {ev} |")
        lines.append("")

    lines.append("## Compact JSON (for paste-back to Claude)")
    lines.append("```json")
    compact = {
        "summary": {"total": total, "pass": passes, "stub": stubs, "fail": fails, "pct": round(100*passes/total)},
        "fails": [r["name"] for r in results if r["status"] == "FAIL"],
        "stubs": [r["name"] for r in results if r["status"] == "STUB"],
    }
    lines.append(json.dumps(compact, indent=2))
    lines.append("```")
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n{'='*60}")
    print(f"Report written to: {REPORT}")
    print(f"PASS: {passes}/{total}  STUB: {stubs}  FAIL: {fails}")
    print(f"Completeness: {round(100*passes/total)}%")
    print(f"{'='*60}\n")


def main() -> None:
    print("Running CIP v2.0 feature audit...\n")
    check_structure()
    check_llm_clients()
    check_agents()
    check_engines()
    check_nlp()
    check_extractor()
    check_metrics()
    check_routes()
    check_templates()
    check_app_boots()
    check_tests_run()
    write_report()


if __name__ == "__main__":
    main()
