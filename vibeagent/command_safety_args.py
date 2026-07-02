from __future__ import annotations


def args_after_operand(args: list[str], operand: str) -> list[str]:
    for index, token in enumerate(args):
        if token.lower() == operand:
            return args[index + 1 :]
    return []


def first_command_operand(args: list[str], options_with_values: set[str]) -> str | None:
    operands = command_operands(args, options_with_values)
    return operands[0] if operands else None


def command_operands(args: list[str], options_with_values: set[str]) -> list[str]:
    operands: list[str] = []
    parse_options = True
    skip_next = False
    for token in args:
        if skip_next:
            skip_next = False
            continue
        if parse_options and token == "--":
            parse_options = False
            continue
        if parse_options and token.startswith("-") and token != "-":
            option = token.split("=", 1)[0]
            if "=" not in token and option in options_with_values:
                skip_next = True
            continue
        operands.append(token)
    return operands
