# CIP v2.0 — Feature Audit Report
_Generated: 2026-04-29T00:23:23.697806Z_

## Summary
- Total checks: **94**
- ✅ PASS:  **62**
- ⚠️ STUB:  **21**  (exists but not real)
- ❌ FAIL:  **11**  (missing or broken)
- **Implementation completeness: 66%**

## Results by category

### AGENT_CONV  (0/9)

| Check | Status | Evidence |
|---|---|---|
| mode_LISTEN | ⚠️ STUB | handler is empty/skeleton |
| mode_NARRATE | ⚠️ STUB | handler is empty/skeleton |
| mode_REFLECT | ❌ FAIL | not implemented |
| mode_BRIDGE | ❌ FAIL | not implemented |
| mode_RECALL | ❌ FAIL | not implemented |
| mode_PREMORTEM | ❌ FAIL | not implemented |
| mode_CRITERIA | ❌ FAIL | not implemented |
| mode_PAIRWISE | ❌ FAIL | not implemented |
| profile_update_parsing | ❌ FAIL | no PROFILE_UPDATE block parsing |

### AGENT_DEVIL  (0/3)

| Check | Status | Evidence |
|---|---|---|
| phase_frameworks | ⚠️ STUB | only 0/4 frameworks referenced |
| stress_test | ❌ FAIL | no stress_test |
| implementation | ⚠️ STUB | contains the word 'stub' |

### AGENT_HYP  (0/1)

| Check | Status | Evidence |
|---|---|---|
| uses_llm | ⚠️ STUB | doesn't actually call LLM |

### AGENT_ORCH  (10/10)

| Check | Status | Evidence |
|---|---|---|
| similarity_check | ✅ PASS |  |
| dimension_assessment | ✅ PASS |  |
| tension_check | ✅ PASS |  |
| mece_audit | ✅ PASS |  |
| hypothesis_evidence | ✅ PASS |  |
| mab_routing | ✅ PASS |  |
| minority_boost | ✅ PASS |  |
| perspective_gap | ✅ PASS |  |
| bayesian_update | ✅ PASS |  |
| stagnation_detection | ✅ PASS |  |

### AGENT_PC  (0/1)

| Check | Status | Evidence |
|---|---|---|
| uses_llm | ⚠️ STUB | doesn't actually call LLM |

### AGENT_RAP  (0/2)

| Check | Status | Evidence |
|---|---|---|
| 11_section_report | ❌ FAIL | no real report structure |
| json_output | ❌ FAIL | no json output |

### APP  (0/1)

| Check | Status | Evidence |
|---|---|---|
| imports_cleanly | ❌ FAIL | ModuleNotFoundError: No module named 'fastapi' |

### ENGINE_AHP  (1/1)

| Check | Status | Evidence |
|---|---|---|
| core_math | ✅ PASS |  |

### ENGINE_BIAS  (0/1)

| Check | Status | Evidence |
|---|---|---|
| implementation | ⚠️ STUB | contains 'placeholder' |

### ENGINE_BRIDGE  (2/3)

| Check | Status | Evidence |
|---|---|---|
| real_similarity | ⚠️ STUB | uses placeholder constant 0.5 |
| bayesian_override | ✅ PASS |  |
| anchoring_detection | ✅ PASS |  |

### ENGINE_CONDORCET  (1/2)

| Check | Status | Evidence |
|---|---|---|
| core_logic | ✅ PASS |  |
| real_cycle_detection | ⚠️ STUB | naive cycle = no Condorcet winner |

### EXTRACTOR  (4/6)

| Check | Status | Evidence |
|---|---|---|
| spacy_analysis | ✅ PASS |  |
| quality_specificity | ⚠️ STUB | specificity hardcoded |
| quality_evidence | ⚠️ STUB | evidence hardcoded to 0.5 |
| quality_novelty_relevance | ✅ PASS |  |
| narrative_parsing | ✅ PASS |  |
| bias_signals | ✅ PASS |  |

### LLM_CLIENT  (4/4)

| Check | Status | Evidence |
|---|---|---|
| call_anthropic | ✅ PASS |  |
| call_openrouter | ✅ PASS |  |
| call_gemini | ✅ PASS |  |
| call_groq | ✅ PASS |  |

### METRICS  (0/2)

| Check | Status | Evidence |
|---|---|---|
| synthetic_idea_ratio | ⚠️ STUB | returns zeros, no real computation |
| died_unfairly | ⚠️ STUB | returns empty list |

### NLP_CLUSTER  (1/1)

| Check | Status | Evidence |
|---|---|---|
| implementation | ✅ PASS |  |

### NLP_DIVERSITY  (0/1)

| Check | Status | Evidence |
|---|---|---|
| implementation | ⚠️ STUB | assumes uniform distribution; ignores clustering |

### NLP_EMBED  (1/1)

| Check | Status | Evidence |
|---|---|---|
| model_loading | ✅ PASS |  |

### ROUTES_ADMIN  (0/1)

| Check | Status | Evidence |
|---|---|---|
| endpoints_coverage | ⚠️ STUB | only 1/6 endpoints |

### ROUTES_FAC  (0/1)

| Check | Status | Evidence |
|---|---|---|
| endpoints_coverage | ⚠️ STUB | only 1/5 endpoints |

### STRUCTURE  (38/38)

| Check | Status | Evidence |
|---|---|---|
| cip/main.py | ✅ PASS |  |
| cip/config.py | ✅ PASS |  |
| cip/db.py | ✅ PASS |  |
| cip/state.py | ✅ PASS |  |
| cip/session.py | ✅ PASS |  |
| cip/observability.py | ✅ PASS |  |
| cip/metrics.py | ✅ PASS |  |
| cip/agents/conversation.py | ✅ PASS |  |
| cip/agents/orchestrator.py | ✅ PASS |  |
| cip/agents/devil.py | ✅ PASS |  |
| cip/agents/rapporteur.py | ✅ PASS |  |
| cip/agents/problem_crystallizer.py | ✅ PASS |  |
| cip/agents/hypothesis.py | ✅ PASS |  |
| cip/agents/idea_extractor.py | ✅ PASS |  |
| cip/engines/criteria.py | ✅ PASS |  |
| cip/engines/condorcet.py | ✅ PASS |  |
| cip/engines/bridging.py | ✅ PASS |  |
| cip/engines/bias.py | ✅ PASS |  |
| cip/nlp/embeddings.py | ✅ PASS |  |
| cip/nlp/clustering.py | ✅ PASS |  |
| cip/nlp/diversity.py | ✅ PASS |  |
| cip/nlp/language.py | ✅ PASS |  |
| cip/llm/clients.py | ✅ PASS |  |
| cip/llm/tier_router.py | ✅ PASS |  |
| cip/llm/tier_map.py | ✅ PASS |  |
| cip/llm/cache.py | ✅ PASS |  |
| cip/admin/routes.py | ✅ PASS |  |
| cip/facilitator/routes.py | ✅ PASS |  |
| cip/websocket/manager.py | ✅ PASS |  |
| cip/templates/admin/dashboard.html | ✅ PASS |  |
| cip/templates/facilitator/dashboard.html | ✅ PASS |  |
| cip/templates/participant/chat.html | ✅ PASS |  |
| cip/templates/replay/session.html | ✅ PASS |  |
| requirements.txt | ✅ PASS |  |
| .env.example | ✅ PASS |  |
| Dockerfile | ✅ PASS |  |
| Procfile | ✅ PASS |  |
| railway.toml | ✅ PASS |  |

### TEMPLATE  (0/4)

| Check | Status | Evidence |
|---|---|---|
| participant_chat | ⚠️ STUB | only 15 lines, skeleton |
| admin_dashboard | ⚠️ STUB | only 12 lines, skeleton |
| facilitator_dashboard | ⚠️ STUB | only 12 lines, skeleton |
| replay_session | ⚠️ STUB | only 13 lines, skeleton |

### TESTS  (0/1)

| Check | Status | Evidence |
|---|---|---|
| pytest_run | ⚠️ STUB | 9 passed, 1 failed |

## Compact JSON (for paste-back to Claude)
```json
{
  "summary": {
    "total": 94,
    "pass": 62,
    "stub": 21,
    "fail": 11,
    "pct": 66
  },
  "fails": [
    "mode_REFLECT",
    "mode_BRIDGE",
    "mode_RECALL",
    "mode_PREMORTEM",
    "mode_CRITERIA",
    "mode_PAIRWISE",
    "profile_update_parsing",
    "stress_test",
    "11_section_report",
    "json_output",
    "imports_cleanly"
  ],
  "stubs": [
    "mode_LISTEN",
    "mode_NARRATE",
    "phase_frameworks",
    "implementation",
    "uses_llm",
    "uses_llm",
    "real_similarity",
    "implementation",
    "real_cycle_detection",
    "implementation",
    "quality_specificity",
    "quality_evidence",
    "synthetic_idea_ratio",
    "died_unfairly",
    "endpoints_coverage",
    "endpoints_coverage",
    "participant_chat",
    "admin_dashboard",
    "facilitator_dashboard",
    "replay_session",
    "pytest_run"
  ]
}
```