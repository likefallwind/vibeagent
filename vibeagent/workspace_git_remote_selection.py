from __future__ import annotations


def select_fetch_remote_from_remotes(
    fetch_remotes: list[dict[str, object]],
    remote: str | None,
) -> dict[str, object]:
    names = sorted({str(item["name"]) for item in fetch_remotes if "name" in item})
    requested = remote.strip() if isinstance(remote, str) else ""
    if remote is not None and not requested:
        return {
            "ok": False,
            "remote": "",
            "remote_url": "",
            "message": "git_fetch remote must be non-empty when provided.",
        }
    if requested and requested not in names:
        return {
            "ok": False,
            "remote": requested,
            "remote_url": "",
            "message": f"Git remote not found: {requested}.",
        }
    if not requested:
        if not names:
            return {
                "ok": False,
                "remote": "",
                "remote_url": "",
                "message": "No git remotes are configured.",
            }
        if len(names) > 1:
            return {
                "ok": False,
                "remote": "",
                "remote_url": "",
                "message": "Multiple git remotes are configured; specify one remote.",
            }
        requested = names[0]

    remote_url = next(
        (str(item["url"]) for item in fetch_remotes if item.get("name") == requested),
        "",
    )
    return {
        "ok": True,
        "remote": requested,
        "remote_url": remote_url,
        "message": "Git remote selected.",
    }
