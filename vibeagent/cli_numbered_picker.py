from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TypeVar


T = TypeVar("T")


def prompt_numbered_choice(
    items: Sequence[T],
    *,
    heading: str,
    item_lines: Callable[[int, T], Sequence[str]],
    prompt_label: str,
    input_func: Callable[[str], str] | None = None,
    print_func: Callable[[str], None] = print,
) -> T:
    if not items:
        raise ValueError("A numbered picker requires at least one item.")
    read_input = input if input_func is None else input_func
    print_func(heading)
    for index, item in enumerate(items, start=1):
        for line in item_lines(index, item):
            print_func(line)
    while True:
        try:
            answer = read_input(
                f"Select {prompt_label} [1-{len(items)}] (blank to cancel): "
            ).strip()
        except (EOFError, KeyboardInterrupt):
            raise ValueError("Selection cancelled.") from None
        if not answer:
            raise ValueError("Selection cancelled.")
        if answer.isascii() and answer.isdigit():
            selected = int(answer)
            if 1 <= selected <= len(items):
                return items[selected - 1]
        print_func(f"Enter a number from 1 to {len(items)}, or leave blank to cancel.")


__all__ = ["prompt_numbered_choice"]
