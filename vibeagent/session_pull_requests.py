from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urlsplit

from .agent_runtime_utils import append_session_event
from .github_pr_context_runtime import select_local_github_repository
from .session_store import list_sessions, read_session_events
from .workspace_core import RunWorkspace


SESSION_PULL_REQUEST_LINKED_EVENT = "session_pull_request_linked"
MAX_PULL_REQUEST_SELECTOR_CHARS = 2_048


@dataclass(frozen=True)
class PullRequestIdentity:
    provider: str
    host: str
    repository: str
    number: int
    url: str

    @property
    def key(self) -> tuple[str, str, str, int]:
        return (self.provider, self.host.lower(), self.repository.lower(), self.number)


def parse_pull_request_url(value: str) -> PullRequestIdentity:
    selector = _validate_selector(value)
    if "%" in selector:
        raise ValueError("Pull request URL cannot contain percent-encoded path components.")
    parsed = urlsplit(selector)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port is not None
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("Pull request URL must be credential-free HTTPS without a port, query, or fragment.")
    host = parsed.hostname.lower()
    parts = parsed.path.strip("/").split("/")
    provider: str
    repository_parts: list[str]
    number_text: str
    if host == "bitbucket.org" and len(parts) == 4 and parts[2] == "pull-requests":
        provider = "bitbucket"
        repository_parts = parts[:2]
        number_text = parts[3]
    elif len(parts) >= 5 and parts[-3:-1] == ["-", "merge_requests"]:
        provider = "gitlab"
        repository_parts = parts[:-3]
        number_text = parts[-1]
    elif len(parts) == 4 and parts[2] == "pull":
        provider = "github"
        repository_parts = parts[:2]
        number_text = parts[3]
    else:
        raise ValueError("Unsupported pull request URL format.")
    if not repository_parts or any(not _valid_path_component(part) for part in repository_parts):
        raise ValueError("Pull request URL contains an invalid repository path.")
    if not number_text.isascii() or not number_text.isdigit() or int(number_text) <= 0:
        raise ValueError("Pull request number must be positive.")
    number = int(number_text)
    repository = "/".join(repository_parts)
    if provider == "gitlab":
        path = f"/{repository}/-/merge_requests/{number}"
    elif provider == "bitbucket":
        path = f"/{repository}/pull-requests/{number}"
    else:
        path = f"/{repository}/pull/{number}"
    return PullRequestIdentity(provider, host, repository, number, f"https://{host}{path}")


def resolve_session_from_pull_request(project_root: Path, selector: str) -> str:
    root = project_root.resolve()
    identity = _identity_from_selector(root, selector)
    for session in list_sessions(root, limit=10_000):
        try:
            links = read_session_pull_requests(root, session.run_id)
        except (OSError, ValueError):
            continue
        if any(link.key == identity.key for link in links):
            return session.run_id
    raise ValueError(f"No local session is linked to pull request {identity.url}.")


def read_session_pull_requests(project_root: Path, run_id: str) -> tuple[PullRequestIdentity, ...]:
    links: list[PullRequestIdentity] = []
    seen: set[tuple[str, str, str, int]] = set()
    for event in read_session_events(project_root, run_id):
        if event.malformed:
            continue
        link = _pull_request_from_event(event.type, event.payload)
        if link is not None and link.key not in seen:
            links.append(link)
            seen.add(link.key)
    return tuple(links)


def inherit_session_pull_requests(workspace: RunWorkspace, source_run_id: str) -> int:
    links = read_session_pull_requests(workspace.root, source_run_id)
    for link in links:
        append_session_event(workspace.session_dir, SESSION_PULL_REQUEST_LINKED_EVENT, asdict(link))
    return len(links)


def _identity_from_selector(project_root: Path, value: str) -> PullRequestIdentity:
    selector = _validate_selector(value)
    if selector.isascii() and selector.isdigit():
        number = int(selector)
        if number <= 0:
            raise ValueError("Pull request number must be positive.")
        workspace = RunWorkspace(
            root=project_root,
            run_id="cli-from-pr",
            session_dir=project_root / ".vibeagent" / "sessions" / "cli-from-pr",
        )
        repository, error = select_local_github_repository(workspace, None)
        if error:
            raise ValueError(f"Cannot resolve pull request number in the current repository: {error}")
        return PullRequestIdentity(
            "github", "github.com", repository, number, f"https://github.com/{repository}/pull/{number}"
        )
    return parse_pull_request_url(selector)


def _pull_request_from_event(event_type: str, payload: dict[str, object]) -> PullRequestIdentity | None:
    if event_type == SESSION_PULL_REQUEST_LINKED_EVENT:
        url = payload.get("url")
    elif event_type in {"tool_result", "subagent_tool_result"} and payload.get("name") == "github_pr_create":
        result = payload.get("result")
        if not isinstance(result, dict) or result.get("kind") != "github_pr_create" or result.get("ok") is not True:
            return None
        url = result.get("url")
    else:
        return None
    if not isinstance(url, str):
        return None
    try:
        return parse_pull_request_url(url)
    except ValueError:
        return None


def _validate_selector(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("Pull request selector must be non-empty.")
    if len(value) > MAX_PULL_REQUEST_SELECTOR_CHARS or any(
        ord(char) < 32 or ord(char) == 127 for char in value
    ):
        raise ValueError("Pull request selector is too long or contains control characters.")
    selector = value.strip()
    if not selector:
        raise ValueError("Pull request selector must be non-empty.")
    if not selector.isascii():
        raise ValueError("Pull request selector must contain ASCII characters only.")
    return selector


def _valid_path_component(value: str) -> bool:
    return bool(value) and value not in {".", ".."} and all(char.isalnum() or char in "._-" for char in value)


__all__ = [
    "PullRequestIdentity",
    "inherit_session_pull_requests",
    "parse_pull_request_url",
    "read_session_pull_requests",
    "resolve_session_from_pull_request",
]
