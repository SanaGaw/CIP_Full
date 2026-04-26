"""Condorcet voting engine.

This module implements ranking using Condorcet and Borda methods.
"""
from __future__ import annotations

from typing import Dict, List, Tuple


def condorcet_rank(pairwise_votes: Dict[Tuple[str, str], int], options: List[str]) -> Dict[str, object]:
    """Rank options using Condorcet winner and Borda count.

    Args:
        pairwise_votes: A dict keyed by (winner, loser) with vote counts.
        options: A list of option identifiers.

    Returns:
        A dict with the Condorcet winner, ranked list, Borda scores,
        polarisation indices and cycle detection flag.
    """
    # Build win matrix
    wins = {opt: 0 for opt in options}
    borda = {opt: 0 for opt in options}
    for (winner, loser), count in pairwise_votes.items():
        wins[winner] += count
        borda[winner] += count
        borda[loser] -= count

    # Determine Condorcet winner (beats all head-to-head)
    condorcet_winner = None
    for opt in options:
        if all(
            pairwise_votes.get((opt, other), 0) >= pairwise_votes.get((other, opt), 0)
            for other in options
            if other != opt
        ):
            condorcet_winner = opt
            break

    # Borda ranking (descending)
    ranked = sorted(options, key=lambda x: borda[x], reverse=True)

    # Simple polarisation: variance of win margins relative to max possible
    total_pairs = len(options) * (len(options) - 1) / 2
    polarization = {opt: 0.0 for opt in options}
    if total_pairs > 0:
        for opt in options:
            # Normalise by total pairs; placeholder logic
            polarization[opt] = abs(borda[opt]) / total_pairs

    # Cycle detection (very basic)
    cycles_detected = False
    # A cycle exists if no Condorcet winner and at least three options
    if condorcet_winner is None and len(options) >= 3:
        cycles_detected = True

    return {
        "condorcet_winner": condorcet_winner,
        "ranked": ranked,
        "borda_scores": borda,
        "polarization": polarization,
        "cycles_detected": cycles_detected,
        "cycle_flag": cycles_detected,
    }