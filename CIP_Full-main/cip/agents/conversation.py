"""Conversation agent modes.

This module defines the ConversationAgent class which manages interactions
with participants across 8 conversation modes. Each mode calls `call_with_tier`
with mode-specific system prompts and implements PROFILE_UPDATE parsing.
"""
from __future__ import annotations

import json
import re
from enum import Enum
from typing import Any, Dict, List

from ..llm.tier_router import call_with_tier
from ..observability import log_trace


class ConversationMode(str, Enum):
    LISTEN = "LISTEN"
    NARRATE = "NARRATE"
    REFLECT = "REFLECT"
    BRIDGE = "BRIDGE"
    RECALL = "RECALL"
    PREMORTEM = "PREMORTEM"
    CRITERIA = "CRITERIA"
    PAIRWISE = "PAIRWISE"


class ConversationAgent:
    """Manage conversation exchanges with a participant."""

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id

    async def handle(self, mode: ConversationMode, user_id: str, messages: List[Dict[str, Any]], session_state: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle a message in a given mode.

        Args:
            mode: The conversation mode requested.
            user_id: ID of the user sending the message.
            messages: The conversation history with user messages.
            session_state: Optional session state with problem_statement, hypothesis, user_profile.

        Returns:
            A dict with the LLM response, profile updates, and tokens used.
        """
        session_state = session_state or {}
        handler_map = {
            ConversationMode.LISTEN: self._listen,
            ConversationMode.NARRATE: self._narrate,
            ConversationMode.REFLECT: self._reflect,
            ConversationMode.BRIDGE: self._bridge,
            ConversationMode.RECALL: self._recall,
            ConversationMode.PREMORTEM: self._premortem,
            ConversationMode.CRITERIA: self._criteria,
            ConversationMode.PAIRWISE: self._pairwise,
        }
        handler = handler_map.get(mode, self._stub_mode)
        return await handler(user_id, messages, session_state)

    def _build_system_prompt(self, mode: str, session_state: Dict[str, Any], user_id: str) -> str:
        """Build mode-specific system prompt with context."""
        problem_statement = session_state.get("problem_statement", "the problem at hand")
        hypothesis = session_state.get("active_hypothesis", {})
        hypothesis_text = hypothesis.get("text", "no active hypothesis")
        user_profile = session_state.get("user_profile", {})

        mode_instructions = {
            "LISTEN": "You are LISTEN mode. Keep responses under 120 words. Ask one clarifying question. No hollow affirmations. Focus on extracting specific details.",
            "NARRATE": "You are NARRATE mode. Prompt the participant to tell a story about the problem. Use one: 'Walk me through the last time this cost something real' or 'Who suffers most from this that no one is talking about?'. Under 120 words.",
            "REFLECT": "You are REFLECT mode. Mirror back the participant's emotional state and key themes. Validate without agreeing. Under 120 words. No hollow affirmations.",
            "BRIDGE": "You are BRIDGE mode. Connect the participant's idea to a different perspective they haven't considered. Introduce contrast or alternative viewpoint. Under 120 words.",
            "RECALL": "You are RECALL mode. Ask the participant to remember a specific past experience relevant to the current topic. 'Tell me about a time when...' Under 120 words.",
            "PREMORTEM": "You are PREMORTEM mode. Ask the participant to imagine this solution has failed and explore why. 'If this failed completely, what went wrong?' Under 120 words.",
            "CRITERIA": "You are CRITERIA mode. Help the participant articulate their decision criteria. 'What would have to be true for this to work? What are your non-negotiables?' Under 120 words.",
            "PAIRWISE": "You are PAIRWISE mode. Present two options for comparison. 'Between A and B, which matters more to you and why?' Under 120 words.",
        }

        base = mode_instructions.get(mode, "Respond appropriately.")
        context = f"\n\nCurrent problem: {problem_statement}\nActive hypothesis: {hypothesis_text}\nParticipant profile summary: {json.dumps(user_profile)[:200]}"
        final_instruction = "\n\nAlways emit a profile update in this format: [PROFILE_UPDATE]{...}[/PROFILE_UPDATE]"

        return f"{base}{context}{final_instruction}"

    def _parse_profile_update(self, text: str) -> tuple:
        """Parse [PROFILE_UPDATE] block from response text.

        Returns:
            Tuple of (cleaned_text, profile_dict)
        """
        pattern = r"\[PROFILE_UPDATE\](.*?)\[/PROFILE_UPDATE\]"
        match = re.search(pattern, text, re.DOTALL)
        if not match:
            return text, {}

        clean_text = text.replace(match.group(0), "").strip()
        try:
            profile = json.loads(match.group(1))
        except json.JSONDecodeError:
            profile = {}

        return clean_text, profile

    async def _listen(self, user_id: str, messages: List[Dict[str, Any]], session_state: Dict[str, Any]) -> Dict[str, Any]:
        """Respond to a participant in LISTEN mode."""
        system = self._build_system_prompt("LISTEN", session_state, user_id)
        call_messages = [{"role": "user", "content": m["text"]} for m in messages]

        result = await call_with_tier(
            task_id="conv.LISTEN",
            system=system,
            messages=call_messages,
            max_tokens=300,
            temperature=0.7,
            session_id=self.session_id,
        )

        text, profile = self._parse_profile_update(result.get("text", ""))

        await log_trace(
            self.session_id, "conv.LISTEN", "conversation",
            f"LISTEN mode response for user {user_id}",
            inputs={"user_id": user_id, "mode": "LISTEN"},
            outputs={"text": text, "profile_update": profile},
            reasoning="LISTEN mode completed"
        )

        return {"text": text, "profile_update": profile, "tokens": result.get("output_tokens", 0)}

    async def _narrate(self, user_id: str, messages: List[Dict[str, Any]], session_state: Dict[str, Any]) -> Dict[str, Any]:
        """Respond in NARRATE mode - prompts participant to tell a story."""
        system = self._build_system_prompt("NARRATE", session_state, user_id)
        call_messages = [{"role": "user", "content": m["text"]} for m in messages]

        result = await call_with_tier(
            task_id="conv.NARRATE",
            system=system,
            messages=call_messages,
            max_tokens=300,
            temperature=0.7,
            session_id=self.session_id,
        )

        text, profile = self._parse_profile_update(result.get("text", ""))

        await log_trace(
            self.session_id, "conv.NARRATE", "conversation",
            f"NARRATE mode response for user {user_id}",
            inputs={"user_id": user_id, "mode": "NARRATE"},
            outputs={"text": text, "profile_update": profile},
            reasoning="NARRATE mode completed"
        )

        return {"text": text, "profile_update": profile, "tokens": result.get("output_tokens", 0)}

    async def _reflect(self, user_id: str, messages: List[Dict[str, Any]], session_state: Dict[str, Any]) -> Dict[str, Any]:
        """Respond in REFLECT mode - mirror emotional state and themes."""
        system = self._build_system_prompt("REFLECT", session_state, user_id)
        call_messages = [{"role": "user", "content": m["text"]} for m in messages]

        result = await call_with_tier(
            task_id="conv.REFLECT",
            system=system,
            messages=call_messages,
            max_tokens=300,
            temperature=0.7,
            session_id=self.session_id,
        )

        text, profile = self._parse_profile_update(result.get("text", ""))

        await log_trace(
            self.session_id, "conv.REFLECT", "conversation",
            f"REFLECT mode response for user {user_id}",
            inputs={"user_id": user_id, "mode": "REFLECT"},
            outputs={"text": text, "profile_update": profile},
            reasoning="REFLECT mode completed"
        )

        return {"text": text, "profile_update": profile, "tokens": result.get("output_tokens", 0)}

    async def _bridge(self, user_id: str, messages: List[Dict[str, Any]], session_state: Dict[str, Any]) -> Dict[str, Any]:
        """Respond in BRIDGE mode - connect to different perspective."""
        system = self._build_system_prompt("BRIDGE", session_state, user_id)
        call_messages = [{"role": "user", "content": m["text"]} for m in messages]

        result = await call_with_tier(
            task_id="conv.BRIDGE",
            system=system,
            messages=call_messages,
            max_tokens=300,
            temperature=0.7,
            session_id=self.session_id,
        )

        text, profile = self._parse_profile_update(result.get("text", ""))

        await log_trace(
            self.session_id, "conv.BRIDGE", "conversation",
            f"BRIDGE mode response for user {user_id}",
            inputs={"user_id": user_id, "mode": "BRIDGE"},
            outputs={"text": text, "profile_update": profile},
            reasoning="BRIDGE mode completed"
        )

        return {"text": text, "profile_update": profile, "tokens": result.get("output_tokens", 0)}

    async def _recall(self, user_id: str, messages: List[Dict[str, Any]], session_state: Dict[str, Any]) -> Dict[str, Any]:
        """Respond in RECALL mode - ask about past experience."""
        system = self._build_system_prompt("RECALL", session_state, user_id)
        call_messages = [{"role": "user", "content": m["text"]} for m in messages]

        result = await call_with_tier(
            task_id="conv.RECALL",
            system=system,
            messages=call_messages,
            max_tokens=300,
            temperature=0.7,
            session_id=self.session_id,
        )

        text, profile = self._parse_profile_update(result.get("text", ""))

        await log_trace(
            self.session_id, "conv.RECALL", "conversation",
            f"RECALL mode response for user {user_id}",
            inputs={"user_id": user_id, "mode": "RECALL"},
            outputs={"text": text, "profile_update": profile},
            reasoning="RECALL mode completed"
        )

        return {"text": text, "profile_update": profile, "tokens": result.get("output_tokens", 0)}

    async def _premortem(self, user_id: str, messages: List[Dict[str, Any]], session_state: Dict[str, Any]) -> Dict[str, Any]:
        """Respond in PREMORTEM mode - explore potential failure."""
        system = self._build_system_prompt("PREMORTEM", session_state, user_id)
        call_messages = [{"role": "user", "content": m["text"]} for m in messages]

        result = await call_with_tier(
            task_id="conv.PREMORTEM",
            system=system,
            messages=call_messages,
            max_tokens=300,
            temperature=0.7,
            session_id=self.session_id,
        )

        text, profile = self._parse_profile_update(result.get("text", ""))

        await log_trace(
            self.session_id, "conv.PREMORTEM", "conversation",
            f"PREMORTEM mode response for user {user_id}",
            inputs={"user_id": user_id, "mode": "PREMORTEM"},
            outputs={"text": text, "profile_update": profile},
            reasoning="PREMORTEM mode completed"
        )

        return {"text": text, "profile_update": profile, "tokens": result.get("output_tokens", 0)}

    async def _criteria(self, user_id: str, messages: List[Dict[str, Any]], session_state: Dict[str, Any]) -> Dict[str, Any]:
        """Respond in CRITERIA mode - articulate decision criteria."""
        system = self._build_system_prompt("CRITERIA", session_state, user_id)
        call_messages = [{"role": "user", "content": m["text"]} for m in messages]

        result = await call_with_tier(
            task_id="conv.CRITERIA",
            system=system,
            messages=call_messages,
            max_tokens=300,
            temperature=0.7,
            session_id=self.session_id,
        )

        text, profile = self._parse_profile_update(result.get("text", ""))

        await log_trace(
            self.session_id, "conv.CRITERIA", "conversation",
            f"CRITERIA mode response for user {user_id}",
            inputs={"user_id": user_id, "mode": "CRITERIA"},
            outputs={"text": text, "profile_update": profile},
            reasoning="CRITERIA mode completed"
        )

        return {"text": text, "profile_update": profile, "tokens": result.get("output_tokens", 0)}

    async def _pairwise(self, user_id: str, messages: List[Dict[str, Any]], session_state: Dict[str, Any]) -> Dict[str, Any]:
        """Respond in PAIRWISE mode - compare two options."""
        system = self._build_system_prompt("PAIRWISE", session_state, user_id)
        call_messages = [{"role": "user", "content": m["text"]} for m in messages]

        result = await call_with_tier(
            task_id="conv.PAIRWISE",
            system=system,
            messages=call_messages,
            max_tokens=300,
            temperature=0.7,
            session_id=self.session_id,
        )

        text, profile = self._parse_profile_update(result.get("text", ""))

        await log_trace(
            self.session_id, "conv.PAIRWISE", "conversation",
            f"PAIRWISE mode response for user {user_id}",
            inputs={"user_id": user_id, "mode": "PAIRWISE"},
            outputs={"text": text, "profile_update": profile},
            reasoning="PAIRWISE mode completed"
        )

        return {"text": text, "profile_update": profile, "tokens": result.get("output_tokens", 0)}

    async def _stub_mode(self, user_id: str, messages: List[Dict[str, Any]], session_state: Dict[str, Any]) -> Dict[str, Any]:
        """Stub fallback for unknown modes."""
        return {"text": "", "profile_update": {}, "tokens": 0}