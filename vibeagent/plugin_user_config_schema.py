from __future__ import annotations

import math
import re
from typing import cast

from .plugin_types import PluginUserConfigOption, PluginUserConfigType


USER_CONFIG_KEY_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")
USER_CONFIG_TYPES = frozenset({"string", "number", "boolean", "directory", "file"})
USER_CONFIG_FIELDS = frozenset(
    {
        "type",
        "title",
        "description",
        "sensitive",
        "required",
        "default",
        "multiple",
        "min",
        "max",
    }
)
MAX_USER_CONFIG_OPTIONS = 50
MAX_USER_CONFIG_STRING_CHARS = 16_000
MAX_USER_CONFIG_MULTIPLE_VALUES = 100


def parse_plugin_user_config(value: object) -> tuple[PluginUserConfigOption, ...]:
    if value is None:
        return ()
    if not isinstance(value, dict):
        raise ValueError("Plugin userConfig must be an object.")
    if len(value) > MAX_USER_CONFIG_OPTIONS:
        raise ValueError(f"Plugin userConfig exceeds {MAX_USER_CONFIG_OPTIONS} options.")
    options: list[PluginUserConfigOption] = []
    for key, raw in value.items():
        if not isinstance(key, str) or not USER_CONFIG_KEY_PATTERN.fullmatch(key):
            raise ValueError("Plugin userConfig keys must be valid 1-64 character identifiers.")
        if not isinstance(raw, dict):
            raise ValueError(f"Plugin userConfig option {key!r} must be an object.")
        unknown = sorted(str(field) for field in raw if field not in USER_CONFIG_FIELDS)
        if unknown:
            raise ValueError(
                f"Plugin userConfig option {key!r} has unsupported fields: {', '.join(unknown)}."
            )
        option_type = raw.get("type")
        if option_type not in USER_CONFIG_TYPES:
            raise ValueError(
                f"Plugin userConfig option {key!r} type must be string, number, boolean, directory, or file."
            )
        title = _bounded_text(raw.get("title"), key, "title", 200)
        description = _bounded_text(raw.get("description"), key, "description", 1_000)
        sensitive = _boolean_field(raw, key, "sensitive", False)
        required = _boolean_field(raw, key, "required", False)
        multiple = _boolean_field(raw, key, "multiple", False)
        if multiple and option_type != "string":
            raise ValueError(f"Plugin userConfig option {key!r} multiple is valid for string type only.")
        minimum = _number_bound(raw, key, "min")
        maximum = _number_bound(raw, key, "max")
        if (minimum is not None or maximum is not None) and option_type != "number":
            raise ValueError(f"Plugin userConfig option {key!r} min/max require number type.")
        if minimum is not None and maximum is not None and minimum > maximum:
            raise ValueError(f"Plugin userConfig option {key!r} min must not exceed max.")
        option = PluginUserConfigOption(
            key=key,
            type=cast(PluginUserConfigType, option_type),
            title=title,
            description=description,
            sensitive=sensitive,
            required=required,
            default=raw.get("default"),
            has_default="default" in raw,
            multiple=multiple,
            minimum=minimum,
            maximum=maximum,
        )
        if option.has_default:
            validate_plugin_user_config_value(option, option.default)
        options.append(option)
    return tuple(sorted(options, key=lambda item: item.key))


def validate_plugin_user_config_value(
    option: PluginUserConfigOption,
    value: object,
) -> object:
    if option.multiple:
        if not isinstance(value, list) or len(value) > MAX_USER_CONFIG_MULTIPLE_VALUES:
            raise ValueError(
                f"Plugin option {option.key!r} must be a list of at most "
                f"{MAX_USER_CONFIG_MULTIPLE_VALUES} strings."
            )
        if any(not _valid_string(item) for item in value):
            raise ValueError(f"Plugin option {option.key!r} must contain bounded strings only.")
        if option.required and not value:
            raise ValueError(f"Required plugin option {option.key!r} must not be empty.")
        return list(value)
    if option.type in {"string", "directory", "file"}:
        if not _valid_string(value):
            raise ValueError(f"Plugin option {option.key!r} must be a bounded string.")
        if option.required and not value:
            raise ValueError(f"Required plugin option {option.key!r} must not be empty.")
        return value
    if option.type == "boolean":
        if not isinstance(value, bool):
            raise ValueError(f"Plugin option {option.key!r} must be a boolean.")
        return value
    if not _finite_number(value):
        raise ValueError(f"Plugin option {option.key!r} must be a finite number.")
    number = float(value)
    if option.minimum is not None and number < option.minimum:
        raise ValueError(f"Plugin option {option.key!r} must be at least {option.minimum:g}.")
    if option.maximum is not None and number > option.maximum:
        raise ValueError(f"Plugin option {option.key!r} must be at most {option.maximum:g}.")
    return value


def _bounded_text(value: object, key: str, field: str, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(
            f"Plugin userConfig option {key!r} {field} must be a non-empty string of at most {maximum} characters."
        )
    return " ".join(value.split())


def _boolean_field(value: dict[object, object], key: str, field: str, default: bool) -> bool:
    selected = value.get(field, default)
    if not isinstance(selected, bool):
        raise ValueError(f"Plugin userConfig option {key!r} {field} must be a boolean.")
    return selected


def _number_bound(value: dict[object, object], key: str, field: str) -> float | None:
    if field not in value:
        return None
    selected = value[field]
    if not _finite_number(selected):
        raise ValueError(f"Plugin userConfig option {key!r} {field} must be a finite number.")
    return float(selected)


def _valid_string(value: object) -> bool:
    return isinstance(value, str) and "\x00" not in value and len(value) <= MAX_USER_CONFIG_STRING_CHARS


def _finite_number(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


__all__ = [
    "MAX_USER_CONFIG_OPTIONS",
    "USER_CONFIG_KEY_PATTERN",
    "parse_plugin_user_config",
    "validate_plugin_user_config_value",
]
