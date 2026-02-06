"""State mutation LLM.

This module translates an Intent + GameState + optional level_context
into a proposal `patch` dict suitable for `engine.patch.apply_patch`.

Design constraints enforced here:
- Never mutate state directly.
- Never decide win conditions.
- Only propose patches (keys: "strict", "vibe").

The implementation is defensive: failures, invalid LLM output, timeouts
or missing client implementations will return an empty patch (`{}`).
Raw LLM outputs are logged at DEBUG level for troubleshooting.

The module attempts to load the mutator model config from
`config/models.dev.yaml` under the `mutator` key and a prompt template
from `llm/prompts/mutate.yaml`. If those are missing, sensible
fallbacks are used.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, Optional

from .tools import call_llm, load_model_config, load_prompt
from engine.state import GameState, strict_state_schema

LOG = logging.getLogger(__name__)


# Initialize model config and prompt at import time so `generate_patch`
# remains focused and deterministic during calls. Tests can override
# these with `set_mutator`.
MODEL_CFG: Dict[str, Any] = load_model_config()
PROMPT_TPL: str = load_prompt("mutate")


def generate_confidence(user_input: str, state: GameState) -> Dict[str, Any]:
	"""Generate a confidence score from user understanding
	   from `user_input` and `state` using an LLM.

	"""
	level_context = level_context or {}


	# Call the LLM (may raise if client not available)
	raw = call_llm(PROMPT_TPL, MODEL_CFG)


	return 0.5

