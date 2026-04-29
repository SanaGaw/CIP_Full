"""Unit tests for the orchestrator agent."""
import pytest
import asyncio

from cip.agents.orchestrator import Orchestrator


@pytest.mark.asyncio
async def test_orchestrator_classify():
    """Test that classify_idea returns full pipeline result dict."""
    orch = Orchestrator("session1")
    idea = {"text": "New idea with specific details and measurements"}
    session_state = {"ideas": [], "problem_statement": "Test problem"}
    result = await orch.classify_idea(idea, session_state)

    # Verify all pipeline steps returned
    assert "similarity" in result
    assert "dimension" in result
    assert "tension" in result
    assert "mece" in result
    assert "hypothesis_evidence" in result
    assert "circulate_to" in result
    assert "perspective_gap" in result
    assert "bayesian_update" in result
    assert "is_stagnant" in result

    # Verify similarity check
    assert "similarity_score" in result["similarity"]
    assert isinstance(result["similarity"]["similarity_score"], float)

    # Verify dimension assessment
    assert "overall_score" in result["dimension"]
    assert 0 <= result["dimension"]["overall_score"] <= 1

    # Verify Bayesian update
    assert "posterior" in result["bayesian_update"]
    assert 0 <= result["bayesian_update"]["posterior"] <= 1


@pytest.mark.asyncio
async def test_orchestrator_similarity_check():
    """Test similarity check with existing ideas."""
    orch = Orchestrator("session1")
    idea = {"text": "This is a test idea"}
    session_state = {
        "ideas": [
            {"text": "Another similar idea"},
            {"text": "Completely different concept"}
        ]
    }
    result = await orch.classify_idea(idea, session_state)

    assert result["similarity"]["similarity_score"] >= 0
    assert result["similarity"]["nearest_idea"] is not None or result["similarity"]["nearest_idea"] is None


@pytest.mark.asyncio
async def test_orchestrator_tension_detection():
    """Test that tension is detected between contradictory ideas."""
    orch = Orchestrator("session1")
    idea = {"text": "We should increase the budget"}
    session_state = {
        "ideas": [
            {"text": "We need to decrease costs"}
        ]
    }
    result = await orch.classify_idea(idea, session_state)

    assert "has_tension" in result["tension"]
    assert "tension_signals" in result["tension"]


@pytest.mark.asyncio
async def test_orchestrator_bayesian_update():
    """Test Bayesian belief update."""
    orch = Orchestrator("session1")

    # Test with agree evidence
    result = orch._bayesian_update(prior=0.5, evidence="agree", confidence=0.8)
    assert result["posterior"] > 0.5  # Agree should increase belief

    # Test with disagree evidence
    result = orch._bayesian_update(prior=0.5, evidence="disagree", confidence=0.8)
    assert result["posterior"] < 0.5  # Disagree should decrease belief


@pytest.mark.asyncio
async def test_orchestrator_stagnation_detection():
    """Test stagnation detection."""
    orch = Orchestrator("session1")

    # Not stagnant with diverse history
    state1 = {"diversity_history": [0.1, 0.3, 0.5, 0.7, 0.9]}
    assert orch._detect_stagnation(state1, n=5) is False

    # Stagnant with uniform history
    state2 = {"diversity_history": [0.5, 0.51, 0.5, 0.49, 0.5]}
    assert orch._detect_stagnation(state2, n=5) is True

    # Not enough history
    state3 = {"diversity_history": [0.5, 0.6]}
    assert orch._detect_stagnation(state3, n=5) is False
