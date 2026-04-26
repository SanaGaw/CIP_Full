"""Unit tests for the idea extractor."""
import pytest

from cip.agents.idea_extractor import extract_ideas, score_quality, parse_narrative_elements, detect_biases


def test_extract_ideas():
    text = "This is the first idea. And this is the second idea!"
    ideas = extract_ideas(text)
    assert len(ideas) == 2


def test_score_quality():
    idea = "We should hire 5 more engineers next quarter."
    score = score_quality(idea)
    assert 0.0 <= score <= 1.0


def test_parse_narrative_elements():
    text = "The team failed because the customer left and we lost revenue."
    elements = parse_narrative_elements(text)
    assert "actors" in elements


def test_detect_biases():
    text = "We already invested so we can't waste."
    biases = detect_biases(text)
    assert "sunk_cost" in biases