"""Unit tests for engines."""
import pytest
import numpy as np

from cip.engines.criteria import compute_ahp_weights, compute_polarization_index
from cip.engines.condorcet import condorcet_rank


def test_ahp_weights():
    matrix = np.array([
        [1, 2, 3],
        [0.5, 1, 2],
        [1/3, 0.5, 1],
    ])
    result = compute_ahp_weights(matrix)
    assert "weights" in result
    assert len(result["weights"]) == 3


def test_polarization_index():
    weights = [
        [0.5, 0.3, 0.2],
        [0.4, 0.4, 0.2],
        [0.6, 0.2, 0.2],
    ]
    result = compute_polarization_index(weights)
    assert len(result) == 3


def test_condorcet_rank():
    votes = {("A", "B"): 3, ("A", "C"): 4, ("B", "C"): 2}
    opts = ["A", "B", "C"]
    result = condorcet_rank(votes, opts)
    assert "ranked" in result