# CIP v2.0 — FIX_PROMPT for Cline

You are continuing an existing CIP v2.0 codebase. Your job is to convert stubs into real implementations until `python check_features.py` reaches 90%+ completeness.

## Working method (strict)

1. Run `python check_features.py` first. Read `CHECK_REPORT.md`.
2. Pick the FIRST failing or stub item from the most critical category (priority order below).
3. Fix it COMPLETELY. No new stubs.
4. Run `python check_features.py` again. Confirm the item moved to PASS.
5. Run `pytest -q` — must still pass.
6. Commit: `git add -A && git commit -m "fix: <category.item> — <one-line>"`
7. Stop. Report: which item you fixed, before/after counts, any blockers.
8. Wait for me to say "continue".

## Priority order (do not deviate)

1. **LLM_CLIENT** (4 items) — implement real HTTP calls. App is useless without these.
2. **EXTRACTOR.quality_*** (3 items) — quality scoring with all 5 dims really computed.
3. **AGENT_ORCH** (10 items) — full 8-step pipeline + Bayesian + stagnation.
4. **AGENT_CONV** (9 items) — all 8 modes implemented + PROFILE_UPDATE parsing.
5. **AGENT_RAP** (2 items) — real 11-section report (md + json).
6. **AGENT_PC + AGENT_HYP** (2 items) — wire to call_with_tier.
7. **AGENT_DEVIL** (3 items) — phase frameworks + stress_test.
8. **ENGINE_BRIDGE.real_similarity, ENGINE_CONDORCET.real_cycle_detection** — replace placeholders.
9. **NLP_DIVERSITY** — use real cluster assignments.
10. **METRICS** (2 items) — real DB-backed computations.
11. **ROUTES_ADMIN, ROUTES_FAC** — full endpoint coverage.
12. **TEMPLATE** (4 items) — real WebSocket UI with JS.

## Hard rules — non-negotiable

- NO STUBS. No `# TODO`, no `pass`, no `return {}` without computation, no "stub response".
- LLM clients use real HTTP via `httpx.AsyncClient`. Test with a real API key during dev. If keys missing, skip provider gracefully (do NOT fail).
- Every fix adds or strengthens a test in `tests/`. Tests must pass with `pytest -q`.
- Never commit `.env`, `*.db`, `*.sqlite3`, `logs/`, `exports/`.
- Use `await log_trace(...)` at every nontrivial decision.
- If you find ambiguity in the original spec, pick the choice that favors observability/debuggability and note it in `BUILD_STATE.md` under "Decisions made".

## Implementation reference cheatsheet (copy these exactly)

### LLM_CLIENT.call_openrouter (real implementation)
```python
import httpx, time
async def call_openrouter(model, system, messages, max_tokens, temperature):
    from ..config import settings
    if not settings.openrouter_api_key:
        raise RuntimeError("OPENROUTER_API_KEY not set")
    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/SanaGaw/CIP_Full",
        "X-Title": "CIP",
    }
    body = {
        "model": model,
        "messages": [{"role": "system", "content": system}] + messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    t0 = time.time()
    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=body)
        r.raise_for_status()
        data = r.json()
    text = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})
    return {
        "text": text,
        "input_tokens": usage.get("prompt_tokens", 0),
        "output_tokens": usage.get("completion_tokens", 0),
        "model": model, "provider": "openrouter",
        "latency_ms": int((time.time() - t0) * 1000),
    }
```

Apply the same pattern for `call_anthropic` (POST `https://api.anthropic.com/v1/messages` with `x-api-key` and `anthropic-version: 2023-06-01`), `call_gemini` (POST `https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key=...`), `call_groq` (POST `https://api.groq.com/openai/v1/chat/completions` with bearer auth — same shape as OpenRouter).

### EXTRACTOR.score_quality (real)
```python
def score_quality(idea, problem_statement="", existing_clusters=None):
    from ..nlp.embeddings import embed
    import numpy as np, re
    # specificity: presence of named entities, numbers, time refs, proper nouns
    spec = 0.0
    if any(c.isdigit() for c in idea): spec += 0.4
    if re.search(r"\b(weeks?|months?|years?|days?|hours?|%|€|\$)", idea, re.I): spec += 0.3
    if re.search(r"\b[A-Z][a-z]+\b", idea): spec += 0.3
    spec = min(1.0, spec)
    # evidence: causal/factual markers
    evid = 0.0
    if re.search(r"\b(because|since|due to|caused by|leads to|results in)\b", idea, re.I): evid += 0.5
    if re.search(r"\b(measured|observed|reported|data shows|according to)\b", idea, re.I): evid += 0.5
    evid = min(1.0, evid)
    # novelty: cosine distance to nearest cluster centroid
    nov = 0.5
    if existing_clusters:
        emb = embed(idea)
        sims = []
        for c in existing_clusters:
            if c.get("centroid") is not None:
                sims.append(float(np.dot(emb, c["centroid"]) / (np.linalg.norm(emb) * np.linalg.norm(c["centroid"]) + 1e-9)))
        nov = 1.0 - max(sims) if sims else 0.7
    # relevance: similarity to problem statement
    rel = 0.5
    if problem_statement:
        e1, e2 = embed(idea), embed(problem_statement)
        rel = float(np.dot(e1, e2) / (np.linalg.norm(e1) * np.linalg.norm(e2) + 1e-9))
        rel = max(0.0, min(1.0, rel))
    # depth: word count + clause count
    words = len(idea.split())
    clauses = len(re.split(r"[,;:]|\b(and|but|because|while|although)\b", idea))
    depth = min(1.0, (words / 30) * 0.6 + (clauses / 4) * 0.4)
    # weighted sum
    score = 0.25*spec + 0.25*evid + 0.20*nov + 0.20*rel + 0.10*depth
    return round(score, 3)
```

### AGENT_ORCH (full pipeline skeleton — implement each method fully)
```python
class Orchestrator:
    async def classify_idea(self, idea, session_state):
        sim_result = await self._similarity_check(idea, session_state)
        dim_result = self._dimension_assessment(idea, session_state)
        tension = await self._tension_check(idea, session_state)
        mece = await self._mece_audit(session_state)
        hyp_ev = self._hypothesis_evidence(idea, session_state.get("active_hypothesis"))
        circulate = self._mab_routing(session_state)
        circulate += self._minority_boost(session_state)
        gap = self._perspective_gap(session_state)
        # log_trace each step with inputs/outputs/reasoning
        return {"similarity": sim_result, "dimension": dim_result, "tension": tension,
                "mece": mece, "hypothesis_evidence": hyp_ev,
                "circulate_to": circulate, "perspective_gap": gap}

    def _bayesian_update(self, prior, evidence, confidence):
        L = {"agree": 3.5, "disagree": 0.28, "neutral": 1.0}.get(evidence, 1.0) * confidence
        post = (prior * L) / (prior * L + (1 - prior) * (1 / L if L > 0 else 1))
        post = max(0.02, min(0.98, post))
        return {"posterior": round(post, 3)}

    def _detect_stagnation(self, session_state, n):
        history = session_state.get("diversity_history", [])
        if len(history) < n: return False
        recent = history[-n:]
        return max(recent) - min(recent) < 0.05
```

### AGENT_CONV (all 8 modes — each calls `call_with_tier` with task-specific system prompt)
Pattern for each mode:
```python
async def _<mode>(self, user_id, messages, session_state):
    system = self._build_system_prompt(mode="<MODE>", session_state=session_state, user_id=user_id)
    call_msgs = [{"role": "user", "content": m["text"]} for m in messages]
    result = await call_with_tier(task_id=f"conv.{mode}", system=system, messages=call_msgs,
                                  max_tokens=300, temperature=0.7, session_id=self.session_id)
    text, profile = self._parse_profile_update(result["text"])
    return {"text": text, "profile_update": profile, "tokens": result["output_tokens"]}

def _parse_profile_update(self, text):
    import re, json
    m = re.search(r"\[PROFILE_UPDATE\](.*?)\[/PROFILE_UPDATE\]", text, re.DOTALL)
    if not m: return text, {}
    clean = text.replace(m.group(0), "").strip()
    try: profile = json.loads(m.group(1))
    except: profile = {}
    return clean, profile
```

The `_build_system_prompt` method assembles a prompt with: 120-word limit, no hollow affirmations, 1 question max, mode-specific instructions, current phase, problem statement, hypothesis, user profile summary, and a final instruction to emit `[PROFILE_UPDATE]{...}[/PROFILE_UPDATE]`.

## Current state (run check_features.py to refresh)

Latest baseline: 53% complete. Main gaps:
- All 4 LLM clients are stubs.
- Orchestrator has 0 of 10 pipeline steps.
- Conversation agent has only 2 of 8 modes (both stubs).
- Rapporteur: no real report.

## Begin

Run `python check_features.py`. Read the report. Fix the FIRST item from priority 1 (LLM_CLIENT). Stop after one fix and report.
