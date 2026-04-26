"""Conversation agent modes.

This module defines the ConversationAgent class which manages interactions
with participants across multiple modes (LISTEN, NARRATE, etc.). For this
pilot build only LISTEN and NARRATE are fully implemented as asynchronous
generators. Other modes are stubbed.
"""
from __future__ import annotations

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

    async def handle(self, mode: ConversationMode, user_id: str, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Handle a message in a given mode.

        Args:
            mode: The conversation mode requested.
            user_id: ID of the user sending the message.
            messages: The conversation history with user messages.

        Returns:
            A dict with the LLM response and any profile updates.
        """
        if mode == ConversationMode.LISTEN:
            return await self._listen(user_id, messages)
        if mode == ConversationMode.NARRATE:
            return await self._narrate(user_id, messages)
        # Stub other modes
        return {"text": "", "profile_update": {}}

    async def _listen(self, user_id: str, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Respond to a participant in LISTEN mode.

        LISTEN mode simply acknowledges input and attempts to extract further
        details by asking a clarifying question. In this stub we call the
        tier router with a fixed system prompt.
        """
        system_prompt = "You are the LISTEN agent. Keep responses under 120 words. Ask one clarifying question."
        call_messages = [{"role": "user", "content": m["text"]} for m in messages]
        result = await call_with_tier(
            task_id="conv.LISTEN",
            system=system_prompt,
            messages=call_messages,
            max_tokens=120,
            temperature=0.7,
            session_id=self.session_id,
        )
        # Parse profile update block (not implemented)
        return {"text": result.get("text", ""), "profile_update": {}}

    async def _narrate(self, user_id: str, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Respond in NARRATE mode.

        NARRATE mode prompts the participant to tell a story about the problem.
        """
        prompt_templates = [
            "Walk me through the last time this cost something real.",
            "If this problem disappeared tomorrow, what changes first?",
            "Who suffers most from this that no one is talking about?",
            "Tell me what you've actually seen — not what you think the answer should be.",
        ]
        system_prompt = "You are the NARRATE agent. Use one of the narrative questions. Keep responses under 120 words."
        call_messages = [{"role": "user", "content": m["text"]} for m in messages]
        result = await call_with_tier(
            task_id="conv.NARRATE",
            system=system_prompt,
            messages=call_messages,
            max_tokens=120,
            temperature=0.7,
            session_id=self.session_id,
        )
        return {"text": result.get("text", ""), "profile_update": {}}