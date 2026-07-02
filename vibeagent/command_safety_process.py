from __future__ import annotations

from .command_safety_args import command_operands


def process_termination_invocation_is_broad(executable: str, args: list[str]) -> bool:
    if executable == "kill":
        signal, targets, read_only = parse_kill_signal_and_targets(args)
        if read_only or process_signal_is_zero(signal):
            return False
        return any(kill_target_is_broad(target) for target in targets)
    if executable in {"pkill", "killall"}:
        signal = parse_matching_kill_signal(args)
        if process_signal_is_zero(signal):
            return False
        return bool(command_operands(args, options_with_values=matching_kill_options_with_values(executable)))
    if executable == "fuser":
        return fuser_invocation_kills_processes(args)
    return False


def parse_kill_signal_and_targets(args: list[str]) -> tuple[str | None, list[str], bool]:
    signal: str | None = None
    targets: list[str] = []
    signal_seen = False
    parse_options = True
    expect_signal = False
    read_only = False
    for token in args:
        lowered = token.lower()
        if expect_signal:
            signal = token
            signal_seen = True
            expect_signal = False
            continue
        if parse_options and token == "--":
            parse_options = False
            continue
        if parse_options and lowered in {"-l", "--list", "-L", "--table"}:
            read_only = True
            continue
        if parse_options and lowered in {"-s", "--signal", "-n"}:
            expect_signal = True
            continue
        if parse_options and lowered.startswith("--signal="):
            signal = token.split("=", 1)[1]
            signal_seen = True
            continue
        if parse_options and token.startswith("-") and not signal_seen and kill_signal_token(token):
            signal = token[1:]
            signal_seen = True
            continue
        targets.append(token)
    return signal, targets, read_only


def kill_signal_token(token: str) -> bool:
    signal = token[1:]
    if signal.isdigit():
        return True
    return signal.lower().removeprefix("sig") in {
        "hup",
        "int",
        "quit",
        "kill",
        "term",
        "usr1",
        "usr2",
        "stop",
        "cont",
        "abrt",
        "alrm",
    }


def process_signal_is_zero(signal: str | None) -> bool:
    if signal is None:
        return False
    return signal.lower().removeprefix("sig") == "0"


def kill_target_is_broad(target: str) -> bool:
    if target in {"0", "1"}:
        return True
    return target.startswith("-") and target[1:].isdigit()


def parse_matching_kill_signal(args: list[str]) -> str | None:
    expect_signal = False
    for token in args:
        lowered = token.lower()
        if expect_signal:
            return token
        if lowered in {"-s", "--signal"}:
            expect_signal = True
            continue
        if lowered.startswith("--signal="):
            return token.split("=", 1)[1]
        if token.startswith("-") and kill_signal_token(token):
            return token[1:]
    return None


def matching_kill_options_with_values(executable: str) -> set[str]:
    shared = {
        "-g",
        "-n",
        "-o",
        "-P",
        "-s",
        "-u",
        "-U",
        "--older",
        "--parent",
        "--signal",
        "--uid",
        "--user",
    }
    if executable == "pkill":
        return shared | {"-G", "-t", "--group", "--pgroup", "--terminal"}
    return shared | {
        "-e",
        "-I",
        "-i",
        "-r",
        "-y",
        "--exact",
        "--ignore-case",
        "--interactive",
        "--regexp",
        "--younger-than",
    }


def fuser_invocation_kills_processes(args: list[str]) -> bool:
    for token in args:
        lowered = token.lower()
        option = lowered.split("=", 1)[0]
        if option == "--kill":
            return True
        if option.startswith("--"):
            continue
        if option.startswith("-") and "k" in option[1:]:
            return True
    return False
