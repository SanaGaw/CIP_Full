"""Condorcet voting engine.

This module implements ranking using Condorcet and Borda methods with real cycle detection.
"""
from __future__ import annotations

from typing import Dict, List, Tuple, Set
from collections import defaultdict, deque


def detect_cycle_in_pairwise(options: List[str], pairwise_votes: Dict[Tuple[str, str], int]) -> Tuple[bool, List[str]]:
    """Detect cycles in pairwise preferences using depth-first search.

    A cycle exists when we can form a chain like A > B > C > ... > A where A beats B,
    B beats C, etc. This violates transitivity and means no Condorcet winner exists.

    Args:
        options: List of options to rank.
        pairwise_votes: Dict of (winner, loser) -> vote count.

    Returns:
        Tuple of (cycle_detected, cycle_path) where cycle_path is the options in the cycle.
    """
    if len(options) < 3:
        return False, []

    # Build adjacency list for strict victories (wins > loses)
    graph = defaultdict(list)
    in_degree = defaultdict(int)

    for opt in options:
        in_degree[opt] = 0

    for (winner, loser), votes in pairwise_votes.items():
        # Only add edge if winner strictly beats loser
        reverse_votes = pairwise_votes.get((loser, winner), 0)
        if votes > reverse_votes:
            graph[winner].append(loser)
            in_degree[loser] += 1

    # Kahn's algorithm to detect cycles and find topological order
    # Nodes with zero in-degree can be processed first
    queue = deque([opt for opt in options if in_degree[opt] == 0])
    processed = []

    while queue:
        node = queue.popleft()
        processed.append(node)
        for neighbor in graph[node]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    # If not all nodes are processed, there's a cycle
    if len(processed) < len(options):
        # Find nodes in the cycle
        remaining = set(options) - set(processed)
        cycle_path = find_cycle_path(graph, list(remaining)[0])
        return True, cycle_path

    return False, []


def find_cycle_path(graph: Dict[str, List[str]], start: str) -> List[str]:
    """Find a cycle path starting from the given node using DFS.

    Args:
        graph: Adjacency list representation of the graph.
        start: Starting node for cycle detection.

    Returns:
        List of nodes forming the cycle.
    """
    visited = set()
    path = []
    stack = [(start, None)]

    while stack:
        node, parent = stack.pop()
        if node in visited:
            # Found cycle - extract it from path
            if node in path:
                cycle_start = path.index(node)
                return path[cycle_start:] + [node]
            return []

        visited.add(node)
        path.append(node)

        for neighbor in graph[node]:
            if neighbor not in visited:
                stack.append((neighbor, node))

    return []


def condorcet_rank(pairwise_votes: Dict[Tuple[str, str], int], options: List[str]) -> Dict[str, object]:
    """Rank options using Condorcet winner and Borda count.

    Args:
        pairwise_votes: A dict keyed by (winner, loser) with vote counts.
        options: A list of option identifiers.

    Returns:
        A dict with the Condorcet winner, ranked list, Borda scores,
        polarisation indices and cycle detection flag.
    """
    if not options:
        return {
            "condorcet_winner": None,
            "ranked": [],
            "borda_scores": {},
            "polarization": {},
            "cycles_detected": False,
            "cycle_path": [],
            "cycle_flag": False,
        }

    # Build win matrix and Borda scores
    wins = {opt: 0 for opt in options}
    borda = {opt: 0 for opt in options}
    for (winner, loser), count in pairwise_votes.items():
        wins[winner] += count
        borda[winner] += count
        borda[loser] -= count

    # Determine Condorcet winner (beats all head-to-head)
    condorcet_winner = None
    for opt in options:
        is_winner = True
        for other in options:
            if other == opt:
                continue
            # opt beats other if votes[opt, other] > votes[other, opt]
            opt_votes = pairwise_votes.get((opt, other), 0)
            other_votes = pairwise_votes.get((other, opt), 0)
            if opt_votes < other_votes:
                is_winner = False
                break
        if is_winner:
            condorcet_winner = opt
            break

    # Borda ranking (descending)
    ranked = sorted(options, key=lambda x: borda[x], reverse=True)

    # Polarisation: variance of win margins
    total_pairs = len(options) * (len(options) - 1) / 2
    polarization = {opt: 0.0 for opt in options}
    if total_pairs > 0:
        for opt in options:
            polarization[opt] = abs(borda[opt]) / total_pairs

    # Real cycle detection using graph analysis
    cycles_detected, cycle_path = detect_cycle_in_pairwise(options, pairwise_votes)

    return {
        "condorcet_winner": condorcet_winner,
        "ranked": ranked,
        "borda_scores": borda,
        "polarization": polarization,
        "cycles_detected": cycles_detected,
        "cycle_path": cycle_path,
        "cycle_flag": cycles_detected,
    }
