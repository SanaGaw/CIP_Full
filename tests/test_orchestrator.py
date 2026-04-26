"""Unit tests for the orchestrator stub."""
import pytest
import asyncio

from cip.agents.orchestrator import Orchestrator


@pytest.mark.asyncio
async def test_orchestrator_classify():
    orch = Orchestrator("session1")
    idea = {"text": "New idea"}
    result = await orch.classify_idea(idea)
    assert result == idea