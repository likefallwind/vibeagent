from __future__ import annotations

from .types import (
    FileInfoAction,
    FileInfoObservation,
    FileInfoResult,
    ImageInfoAction,
    ImageInfoObservation,
    ImageInfoResult,
    ViewImageAction,
    ViewImageObservation,
)
from .workspace import read_project_file_info, read_project_image_info, read_project_image_payload
from .workspace_core import RunWorkspace


def file_info_observation(workspace: RunWorkspace, action: FileInfoAction) -> FileInfoObservation:
    files: list[FileInfoResult] = []
    for path in action.paths:
        try:
            info = read_project_file_info(workspace, path)
            files.append(FileInfoResult(**info))
        except ValueError as error:
            files.append(
                FileInfoResult(
                    path=path,
                    ok=False,
                    exists=False,
                    is_file=False,
                    is_dir=False,
                    size_bytes=None,
                    line_count=None,
                    is_binary=None,
                    message=str(error),
                )
            )
    ok_count = sum(1 for item in files if item.ok)
    return FileInfoObservation(
        kind="file_info",
        files=files,
        message=f"Inspected {ok_count}/{len(files)} path(s).",
    )


def image_info_observation(workspace: RunWorkspace, action: ImageInfoAction) -> ImageInfoObservation:
    images: list[ImageInfoResult] = []
    for path in action.paths:
        try:
            info = read_project_image_info(workspace, path)
            images.append(ImageInfoResult(**info))
        except ValueError as error:
            images.append(
                ImageInfoResult(
                    path=path,
                    ok=False,
                    exists=False,
                    is_file=False,
                    size_bytes=None,
                    format=None,
                    mime_type=None,
                    width=None,
                    height=None,
                    message=str(error),
                )
            )
    ok_count = sum(1 for item in images if item.ok)
    return ImageInfoObservation(
        kind="image_info",
        images=images,
        message=f"Inspected {ok_count}/{len(images)} image(s).",
    )


def view_image_observation(workspace: RunWorkspace, action: ViewImageAction) -> ViewImageObservation:
    try:
        payload = read_project_image_payload(workspace, action.path, action.max_bytes)
        return ViewImageObservation(
            kind="view_image",
            ok=True,
            path=action.path,
            size_bytes=int(payload["size_bytes"]),
            format=str(payload["format"]),
            mime_type=str(payload["mime_type"]),
            width=int(payload["width"]),
            height=int(payload["height"]),
            max_bytes=action.max_bytes,
            message=f"Loaded image for model inspection: {action.path}",
        )
    except ValueError as error:
        return ViewImageObservation(
            kind="view_image",
            ok=False,
            path=action.path,
            size_bytes=None,
            format=None,
            mime_type=None,
            width=None,
            height=None,
            max_bytes=action.max_bytes,
            message=str(error),
        )
