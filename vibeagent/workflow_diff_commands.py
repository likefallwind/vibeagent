from __future__ import annotations

from .workflow_diff_context_commands import (
    DIFF_CONTEXTS_USAGE,
    format_diff_contexts_report_text,
    get_diff_contexts_report,
    get_diff_contexts_text,
    serialize_file_context_result,
)
from .workflow_diff_hunk_commands import (
    DIFF_HUNKS_USAGE,
    format_diff_hunk_lines,
    format_diff_hunks_report_text,
    get_diff_hunks_report,
    get_diff_hunks_text,
    serialize_diff_hunk,
)
from .workflow_plain_diff_commands import DIFF_USAGE, format_diff_report_text, get_diff_report, get_diff_text
from .workflow_diff_utils import (
    clip_with_flag,
    parse_diff_argument,
    usage_error as _usage_error,
    validate_diff_contexts_limits,
    validate_diff_hunks_limits,
)
