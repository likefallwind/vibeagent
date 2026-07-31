from __future__ import annotations

from .prompt_observation_generic_code_intel import format_generic_code_intel_observation
from .prompt_observation_python_intel import format_python_intel_observation
from .types import Observation


def format_code_intel_observation(index: int, observation: Observation) -> str | None:
    python_line = format_python_intel_observation(index, observation)
    if python_line is not None:
        return python_line
    return format_generic_code_intel_observation(index, observation)
