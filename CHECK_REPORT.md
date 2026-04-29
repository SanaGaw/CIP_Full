# CIP v2.0 — Feature Audit Report
_Generated: 2026-04-29T00:34:24.172522Z_

## Summary
- Total checks: **95**
- ✅ PASS:  **77**
- ⚠️ STUB:  **18**  (exists but not real)
- ❌ FAIL:  **0**  (missing or broken)
- **Implementation completeness: 81%**

## Results by category

### AGENT_CONV  (9/9)

| Check | Status | Evidence |
|---|---|---|
| mode_LISTEN | ✅ PASS |  |
| mode_NARRATE | ✅ PASS |  |
| mode_REFLECT | ✅ PASS |  |
| mode_BRIDGE | ✅ PASS |  |
| mode_RECALL | ✅ PASS |  |
| mode_PREMORTEM | ✅ PASS |  |
| mode_CRITERIA | ✅ PASS |  |
| mode_PAIRWISE | ✅ PASS |  |
| profile_update_parsing | ✅ PASS |  |

### AGENT_DEVIL  (2/3)

| Check | Status | Evidence |
|---|---|---|
| phase_frameworks | ⚠️ STUB | only 0/4 frameworks referenced |
| stress_test | ✅ PASS |  |
| implementation | ✅ PASS |  |

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

### AGENT_RAP  (1/2)

| Check | Status | Evidence |
|---|---|---|
| 11_section_report | ⚠️ STUB | only 3/11 sections |
| json_output | ✅ PASS |  |

### APP  (2/2)

| Check | Status | Evidence |
|---|---|---|
| imports_cleanly | ✅ PASS |  |
| health_endpoint | ✅ PASS |  |

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

### TESTS  (1/1)

| Check | Status | Evidence |
|---|---|---|
| pytest_run | ✅ PASS | 14 passed, 0 failed |

## Compact JSON (for paste-back to Claude)
```json
{
  "summary": {
    "total": 95,
    "pass": 77,
    "stub": 18,
    "fail": 0,
    "pct": 81
  },
  "fails": [],
  "stubs": [
    "phase_frameworks",
    "11_section_report",
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
    "replay_session"
  ]
}
```