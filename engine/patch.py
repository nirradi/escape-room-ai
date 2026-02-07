"""Patch schema and utilities.

This module applies LLM-generated patches to the game state.

Patches describe desired state changes in two categories:
  - strict: Changes to authoritative game state that must be validated
  - vibe: Ambient narrative state that can be flexible

Key design principles:
  - Deterministic and testable
  - Patches are declarative (desired state), not imperative (instructions)
  - Validation is strict for game-critical state, permissive for narrative
"""

from dataclasses import dataclass, field
from typing import Any
from copy import deepcopy

from engine.state import GameState, StrictState, VibeState


# Type alias for a patch dictionary
Patch = dict[str, Any]

# Classification score adjustments
CLASSIFICATION_SCORE_DELTAS = {
    "COMMITTING_TO_CORRECT_MODEL": 0.25,
    "SOME_UNDERSTANDING": 0.10,
    "NEUTRAL_ACTION": 0.0,
    "COMMITTING_TO_INCORRECT_MODEL": -0.15,
    "INVALID": 0.0,  # No score change for invalid LLM output
}


def classification_to_patch(classification_level: str, current_confidence: float) -> Patch:
    """Convert a classification level to a patch that updates the confidence score.
    
    Args:
        classification_level: One of COMMITTING_TO_CORRECT_MODEL, SOME_UNDERSTANDING, NEUTRAL_ACTION, COMMITTING_TO_INCORRECT_MODEL.
        current_confidence: Current solutionConfidenceScore (0.0 to 1.0).
        
    Returns:
        A patch dict that updates solutionConfidenceScore based on the classification.
    """
    delta = CLASSIFICATION_SCORE_DELTAS.get(classification_level, 0.0)
    new_score = max(0.0, min(1.0, current_confidence + delta))
    
    return {
        "strict": {
            "solutionConfidenceScore": new_score
        }
    }


@dataclass
class ValidationError:
    """A single validation error in strict state."""
    field: str
    reason: str
    attempted_value: Any


@dataclass
class PatchResult:
    """Result of applying a patch to game state.
    
    Attributes:
        success: Whether the patch was fully applied.
        state: The resulting game state (original if failed, modified otherwise).
        strict_errors: Validation errors encountered in strict patches.
        warnings: Non-fatal issues encountered.
    """
    success: bool
    state: GameState
    strict_errors: list[ValidationError] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _apply_strict_patch(
    current_strict: StrictState,
    patch_dict: dict[str, Any]
) -> tuple[StrictState, list[ValidationError]]:
    """Apply and validate a strict patch.
    
    This function preserves the original state and only modifies what is
    explicitly provided in the patch, after validation passes.
    
    Args:
        current_strict: Current strict state.
        patch_dict: Patch data for strict state.
        
    Returns:
        Tuple of (updated_strict_state, validation_errors).
        If any field fails validation, that field is not applied.
        Returns original state with errors if validation fails.
    """
    errors: list[ValidationError] = []
    
    # Create a working copy
    updated = deepcopy(current_strict)
    
    # apply and validate fields
    for key, value in patch_dict.items():
        if not hasattr(current_strict, key):
            errors.append(ValidationError(
                field=key,
                reason="Unknown field",
                attempted_value=value
            ))
            continue
        
        # Example validation: solutionConfidenceScore must be 0.0 to 1.0
        if key == "solutionConfidenceScore":
            if not isinstance(value, (float, int)) or not (0.0 <= value <= 1.0):
                errors.append(ValidationError(
                    field=key,
                    reason="Must be a float between 0.0 and 1.0",
                    attempted_value=value
                ))
                continue
        
        # Apply the validated change
        setattr(updated, key, value)
    
    return updated, errors


def _apply_vibe_patch(
    current_vibe: VibeState,
    patch_dict: dict[str, Any]
) -> tuple[VibeState, list[str]]:
    """Apply a vibe patch permissively.
    
    Vibe patches have minimal validation - just structural sanity checks.
    Missing or mistyped fields are tolerated to keep narrative flexible.
    
    Args:
        current_vibe: Current vibe state.
        patch_dict: Patch data for vibe state.
        
    Returns:
        Tuple of (updated_vibe_state, warnings).
    """
    warnings: list[str] = []
    
    # Create a working copy
    updated = deepcopy(current_vibe)
    
    # Apply fields permissively
    for key, value in patch_dict.items():
        if hasattr(updated, key):
            setattr(updated, key, value)
        else:
            warnings.append(f"Unknown vibe field '{key}', skipping")
    
    return updated, warnings


def apply_patch(
    state: GameState,
    patch: Patch,
) -> PatchResult:
    """Apply a patch to the game state.
    
    Patches have two top-level keys:
      - strict: Validated, game-critical state changes
      - vibe: Flexible, narrative-only state changes
    
    Strict patches are validated before application. If validation fails,
    those fields are not applied. Vibe patches are applied permissively.
    Each call also advances the turn counter unless explicitly patched.
    
    Args:
        state: Current game state.
        patch: Patch dict with "strict" and/or "vibe" keys.
        
    Returns:
        PatchResult: Contains updated state, errors, and warnings.
        
    Example:
        patch = {
            "strict": {
               "solutionConfidenceScore": 0.7
            },
            "vibe": {
                "name": ["Mysterious Stranger"]
            }
        }
        result = apply_patch(state, patch)
        if result.success:
            state = result.state
    """

    # Start with a copy of the current state
    updated_state = deepcopy(state)
    all_errors: list[ValidationError] = []
    all_warnings: list[str] = []
    
    # Apply strict patches with validation
    if "strict" in patch:
        strict_patch = patch["strict"]
        if isinstance(strict_patch, dict):
            updated_strict, strict_errors = _apply_strict_patch(
                updated_state.strict,
                strict_patch
            )
            all_errors.extend(strict_errors)
            updated_state.strict = updated_strict
        else:
            all_warnings.append("strict patch should be a dict, skipping")
    
    # Apply vibe patches permissively
    if "vibe" in patch:
        vibe_patch = patch["vibe"]
        if isinstance(vibe_patch, dict):
            updated_vibe, vibe_warnings = _apply_vibe_patch(
                updated_state.vibe,
                vibe_patch
            )
            all_warnings.extend(vibe_warnings)
            updated_state.vibe = updated_vibe
        else:
            all_warnings.append("vibe patch should be a dict, skipping")

    # Success if no strict validation errors occurred
    success = len(all_errors) == 0
    
    return PatchResult(
        success=success,
        state=updated_state,
        strict_errors=all_errors,
        warnings=all_warnings
    )
