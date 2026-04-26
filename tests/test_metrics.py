"""Unit tests for metrics."""
import pytest
import asyncio

from cip.metrics import compute_synthetic_idea_ratio, compute_died_unfairly


@pytest.mark.asyncio
async def test_compute_synthetic_idea_ratio():
    result = await compute_synthetic_idea_ratio("session1")
    assert "synthetic_ratio" in result


@pytest.mark.asyncio
async def test_compute_died_unfairly():
    result = await compute_died_unfairly("session1")
    assert isinstance(result, list)