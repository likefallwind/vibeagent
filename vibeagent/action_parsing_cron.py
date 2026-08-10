from __future__ import annotations

import re
from typing import Any

from .action_cron_types import CronCreateAction, CronDeleteAction, CronListAction
from .action_parsing_scalars import ActionParseError
from .cron_expression import CronExpressionError, parse_cron_expression


CRON_ACTION_TYPES = {"cron_create", "cron_list", "cron_delete"}
MAX_CRON_PROMPT_CHARS = 25_000


def parse_cron_action(action_type: object, value: dict[str, Any], raw: str) -> object | None:
    if action_type not in CRON_ACTION_TYPES:
        return None
    if action_type == "cron_list":
        return CronListAction(type="cron_list")
    if action_type == "cron_delete":
        task_id = value.get("task_id")
        if not isinstance(task_id, str) or re.fullmatch(r"[0-9a-f]{8}", task_id) is None:
            raise ActionParseError("CronDelete taskId must be an 8-character lowercase hexadecimal ID.", raw)
        return CronDeleteAction(type="cron_delete", task_id=task_id)

    cron = value.get("cron")
    prompt = value.get("prompt")
    recurring = value.get("recurring")
    if not isinstance(cron, str) or not cron.strip():
        raise ActionParseError("CronCreate cron must be a non-empty string.", raw)
    try:
        parsed = parse_cron_expression(cron)
    except CronExpressionError as error:
        raise ActionParseError(f"Invalid CronCreate cron expression: {error}", raw) from error
    if not isinstance(prompt, str) or not prompt.strip():
        raise ActionParseError("CronCreate prompt must be a non-empty string.", raw)
    prompt = prompt.strip()
    if len(prompt) > MAX_CRON_PROMPT_CHARS:
        raise ActionParseError(
            f"CronCreate prompt must contain at most {MAX_CRON_PROMPT_CHARS} characters.", raw
        )
    if not isinstance(recurring, bool):
        raise ActionParseError("CronCreate recurring must be a boolean.", raw)
    return CronCreateAction(type="cron_create", cron=parsed.source, prompt=prompt, recurring=recurring)


__all__ = ["CRON_ACTION_TYPES", "MAX_CRON_PROMPT_CHARS", "parse_cron_action"]
