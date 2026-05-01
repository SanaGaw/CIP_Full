"""Criteria engine using Analytic Hierarchy Process (AHP).

This module provides functions to compute AHP weights and criterion
polarisation indices.
"""
from __future__ import annotations

from typing import Dict, List, Tuple

import numpy as np


def compute_ahp_weights(pairwise_matrix: np.ndarray) -> Dict[str, object]:
    """Compute AHP priority weights and consistency ratio.

    Args:
        pairwise_matrix: A square numpy array of pairwise comparisons.

    Returns:
        A dict containing weights, consistency_ratio, and is_consistent.
    """
    # Normalise columns
    col_sums = pairwise_matrix.sum(axis=0)
    normalised = pairwise_matrix / col_sums
    priority_vector = normalised.mean(axis=1)
    # Compute consistency
    n = pairwise_matrix.shape[0]
    lamda_max = (pairwise_matrix.dot(priority_vector) / priority_vector).mean()
    ci = (lamda_max - n) / (n - 1) if n > 2 else 0
    # Random index values for matrices up to size 10
    RI = {
        1: 0.0,
        2: 0.0,
        3: 0.58,
        4: 0.9,
        5: 1.12,
        6: 1.24,
        7: 1.32,
        8: 1.41,
        9: 1.45,
        10: 1.49,
    }
    ri = RI.get(n, 1.49)
    cr = ci / ri if ri > 0 else 0
    return {
        "weights": priority_vector.tolist(),
        "consistency_ratio": round(cr, 4),
        "is_consistent": cr < 0.1,
    }


def compute_polarization_index(weight_vectors: List[List[float]]) -> List[float]:
    """Compute a polarisation index per criterion.

    Args:
        weight_vectors: A list of weight vectors from multiple participants.

    Returns:
        A list of polarisation values between 0 and 1 for each criterion.
    """
    if not weight_vectors:
        return []
    arr = np.array(weight_vectors)
    variances = arr.var(axis=0)
    # Maximum variance for probabilities occurs at 0.25 for binary; scale accordingly.
    return (variances / 0.25).tolist()