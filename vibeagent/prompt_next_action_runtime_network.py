from __future__ import annotations

from .types import Observation


def _port_check_next_action_instruction(base: str, latest: Observation) -> str:
    host = str(getattr(latest, "host", "") or "host")
    port = int(getattr(latest, "port", 0) or 0)
    target = f"{host}:{port}" if port else host
    if getattr(latest, "reachable", False):
        return (
            f"{base} Port check reached {target}. Continue with http_check/http_fetch or the dependent workflow, "
            "or answer directly if readiness is proven."
        )
    return (
        f"{base} Port check could not reach {target}. Inspect the server process with list_processes/read_process, "
        "start the required command if needed, or fix the bind/port before retrying."
    )


def _http_check_next_action_instruction(base: str, latest: Observation) -> str:
    url = str(getattr(latest, "url", "") or "the URL")
    if getattr(latest, "reachable", False) and getattr(latest, "matched", False):
        return f"{base} HTTP check reached {url} and matched the expected pattern. Continue the dependent check or answer directly if complete."
    if getattr(latest, "reachable", False):
        status = getattr(latest, "status", None)
        return (
            f"{base} HTTP check reached {url}"
            f"{' with status ' + str(status) if status is not None else ''} but did not prove readiness. "
            "Inspect the response body, adjust the pattern, or continue with http_fetch/read_process to diagnose."
        )
    return (
        f"{base} HTTP check could not reach {url}. Inspect server logs with read_process, verify the port with port_check, "
        "or start/fix the service before retrying."
    )


def _http_fetch_next_action_instruction(base: str, latest: Observation) -> str:
    url = str(getattr(latest, "url", "") or "the URL")
    if not getattr(latest, "reachable", False):
        return f"{base} HTTP fetch could not reach {url}. Inspect the server process, port, or error before retrying."
    if not getattr(latest, "ok", False):
        status = getattr(latest, "status", None)
        return (
            f"{base} HTTP fetch reached {url}"
            f"{' with status ' + str(status) if status is not None else ''}. "
            "Use the response body and server logs to fix the issue, then rerun the relevant HTTP check."
        )
    if getattr(latest, "body_truncated", False):
        return f"{base} HTTP fetch succeeded but the body was truncated. Re-fetch a narrower endpoint or inspect the relevant source/logs."
    return f"{base} HTTP fetch succeeded. Use the response to decide the next fix, dependent check, or final answer."


def _web_fetch_next_action_instruction(base: str, latest: Observation) -> str:
    url = str(getattr(latest, "url", "") or "the URL")
    if getattr(latest, "ok", False):
        return f"{base} Public document fetch succeeded for {url}. Use the returned text to continue or answer directly."
    return f"{base} Public document fetch failed for {url}. Inspect the safety or network error and use another public source if needed."
