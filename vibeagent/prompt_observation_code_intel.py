from __future__ import annotations

from .prompt_observation_utils import truncate
from .types import Observation


def format_code_intel_observation(index: int, observation: Observation) -> str | None:
    if observation.kind == "python_symbols":
        parts = [f"{index}. python_symbols: {observation.message}"]
        for file in observation.files:
            parts.append(f"file: {file.path} ok={str(file.ok).lower()} message={file.message}")
            if file.imports:
                parts.append("imports:\n" + "\n".join(file.imports[:40]))
            if file.symbols:
                parts.append(
                    "symbols:\n"
                    + "\n".join(
                        (
                            f"- {symbol.kind} {symbol.name} "
                            f"line={symbol.line} endLine={symbol.end_line or 'unknown'} "
                            f"parent={symbol.parent or '.'}"
                        )
                        for symbol in file.symbols[:120]
                    )
                )
        return "\n".join(parts)

    if observation.kind == "code_outline":
        parts = [f"{index}. code_outline: {observation.message}"]
        for file in observation.files:
            parts.append(
                (
                    f"file: {file.path} language={file.language or '.'} "
                    f"ok={str(file.ok).lower()} message={file.message}"
                )
            )
            if file.imports:
                parts.append("imports:\n" + "\n".join(file.imports[:40]))
            if file.symbols:
                parts.append(
                    "symbols:\n"
                    + "\n".join(
                        (
                            f"- {symbol.kind} {symbol.name} "
                            f"line={symbol.line} parent={symbol.parent or '.'}"
                        )
                        for symbol in file.symbols[:120]
                    )
                )
        return "\n".join(parts)

    if observation.kind == "python_check":
        parts = [
            (
                f"{index}. python_check {observation.path or '.'}: {observation.message} "
                f"checked={len(observation.files)}/{observation.total} "
                f"truncated={str(observation.truncated).lower()}"
            )
        ]
        for file in observation.files[:120]:
            location = ""
            if file.line is not None:
                location = f" line={file.line} column={file.column or 'unknown'}"
            parts.append(f"file: {file.path} ok={str(file.ok).lower()}{location} message={file.message}")
        return "\n".join(parts)

    if observation.kind == "config_check":
        parts = [
            (
                f"{index}. config_check {observation.path or '.'}: {observation.message} "
                f"checked={len(observation.files)}/{observation.total} "
                f"truncated={str(observation.truncated).lower()}"
            )
        ]
        for file in observation.files[:120]:
            location = ""
            if file.line is not None:
                location = f" line={file.line} column={file.column or 'unknown'}"
            parts.append(
                (
                    f"file: {file.path} format={file.format} ok={str(file.ok).lower()}"
                    f"{location} message={file.message}"
                )
            )
        return "\n".join(parts)

    if observation.kind == "python_dependencies":
        parts = [
            (
                f"{index}. python_dependencies {observation.path or '.'}: {observation.message} "
                f"files={len(observation.files)}/{observation.total} "
                f"truncated={str(observation.truncated).lower()}"
            )
        ]
        for file in observation.files[:80]:
            parts.append(
                (
                    f"file: {file.path} module={file.module or '.'} ok={str(file.ok).lower()} "
                    f"local={','.join(file.local_modules[:20]) or '-'} "
                    f"external={','.join(file.external_modules[:20]) or '-'} "
                    f"message={file.message}"
                )
            )
            for import_ref in file.imports[:80]:
                parts.append(
                    (
                        f"import: line={import_ref.line} kind={import_ref.kind} "
                        f"module={import_ref.module or '.'} name={import_ref.name or '-'} "
                        f"target={import_ref.target or '.'} local={str(import_ref.local).lower()}"
                    )
                )
        return "\n".join(parts)

    if observation.kind == "code_dependencies":
        parts = [
            (
                f"{index}. code_dependencies {observation.path or '.'}: {observation.message} "
                f"files={len(observation.files)}/{observation.total} "
                f"truncated={str(observation.truncated).lower()}"
            )
        ]
        for file in observation.files[:80]:
            parts.append(
                (
                    f"file: {file.path} language={file.language} ok={str(file.ok).lower()} "
                    f"dependencies={','.join(file.dependencies[:40]) or '-'} "
                    f"message={file.message}"
                )
            )
            for import_ref in file.imports[:80]:
                parts.append(
                    (
                        f"import: line={import_ref.line} kind={import_ref.kind} "
                        f"source={import_ref.source or '.'} raw={import_ref.raw}"
                    )
                )
        return "\n".join(parts)

    if observation.kind == "code_references":
        parts = [
            (
                f"{index}. code_references {observation.symbol}: {observation.message} "
                f"shown={len(observation.references)}/{observation.total} "
                f"path={observation.path or '.'} "
                f"truncated={str(observation.truncated).lower()}"
            )
        ]
        for reference in observation.references[:160]:
            parts.append(
                (
                    f"reference: {reference.path}:{reference.line}:{reference.column} "
                    f"language={reference.language} context={reference.context}"
                )
            )
        return "\n".join(parts)

    if observation.kind == "code_reference_contexts":
        parts = [
            (
                f"{index}. code_reference_contexts {observation.symbol}: {observation.message} "
                f"shown={len(observation.contexts)}/{observation.total} "
                f"path={observation.path or '.'} "
                f"context_lines={observation.context_lines} "
                f"truncated={str(observation.truncated).lower()}"
            )
        ]
        for context in observation.contexts[:80]:
            parts.append(
                (
                    f"reference: {context.path}:{context.line}:{context.column} "
                    f"language={context.language or 'unknown'} kind={context.kind} "
                    f"range={context.start_line}-{context.end_line} "
                    f"truncated={str(context.truncated).lower()} "
                    f"match={context.matched_line}"
                )
            )
            parts.append("content:\n" + truncate(context.content))
        return "\n".join(parts)

    if observation.kind == "code_definitions":
        parts = [
            (
                f"{index}. code_definitions {observation.symbol}: {observation.message} "
                f"path={observation.path or '.'} truncated={str(observation.truncated).lower()}"
            )
        ]
        for definition in observation.definitions[:80]:
            parts.append(
                (
                    f"definition: {definition.path}:{definition.line}-{definition.end_line} "
                    f"language={definition.language} {definition.kind} {definition.name} "
                    f"truncated={str(definition.truncated).lower()}"
                )
            )
            parts.append("content:\n" + truncate(definition.content))
        if observation.errors:
            parts.append("errors:\n" + "\n".join(observation.errors[:20]))
        return "\n".join(parts)

    if observation.kind == "code_rename_preview":
        parts = [
            (
                f"{index}. code_rename_preview {observation.symbol}->{observation.new_name}: "
                f"{observation.message} path={observation.path or '.'} "
                f"files={len(observation.files)}/{observation.total_files} "
                f"replacements={observation.total_replacements} "
                f"truncated={str(observation.truncated).lower()}"
            )
        ]
        for file in observation.files[:40]:
            parts.append(
                (
                    f"file: {file.path} language={file.language} replacements={len(file.replacements)} "
                    f"truncated={str(file.truncated).lower()}"
                )
            )
            for replacement in file.replacements[:80]:
                parts.append(
                    (
                        f"replace: {replacement.line}:{replacement.column}-{replacement.end_column} "
                        f"{replacement.old}->{replacement.new} context={replacement.context}"
                    )
                )
            parts.append("diff:\n" + truncate(file.diff))
        if observation.errors:
            parts.append("errors:\n" + "\n".join(observation.errors[:20]))
        return "\n".join(parts)

    if observation.kind == "code_rename":
        parts = [
            (
                f"{index}. code_rename {observation.symbol}->{observation.new_name}: "
                f"{observation.message} path={observation.path or '.'} "
                f"files={len(observation.files)}/{observation.total_files} "
                f"replacements={observation.total_replacements}"
            )
        ]
        if observation.diff:
            parts.append("diff:\n" + truncate(observation.diff))
        if observation.errors:
            parts.append("errors:\n" + "\n".join(observation.errors[:20]))
        return "\n".join(parts)

    if observation.kind == "python_definitions":
        parts = [
            (
                f"{index}. python_definitions {observation.symbol}: {observation.message} "
                f"path={observation.path or '.'} truncated={str(observation.truncated).lower()}"
            )
        ]
        for definition in observation.definitions[:80]:
            parts.append(
                (
                    f"definition: {definition.path}:{definition.line}-{definition.end_line} "
                    f"{definition.kind} {definition.qualified_name} "
                    f"truncated={str(definition.truncated).lower()}"
                )
            )
            parts.append("content:\n" + truncate(definition.content))
        if observation.errors:
            parts.append("errors:\n" + "\n".join(observation.errors[:20]))
        return "\n".join(parts)

    if observation.kind == "python_calls":
        parts = [
            (
                f"{index}. python_calls {observation.symbol}: {observation.message} "
                f"path={observation.path or '.'} truncated={str(observation.truncated).lower()}"
            )
        ]
        for call in observation.calls[:120]:
            parts.append(
                (
                    f"{call.path}:{call.line}:{call.column}: "
                    f"caller={call.caller or '.'} callee={call.callee} {call.context}"
                )
            )
        if observation.errors:
            parts.append("errors:\n" + "\n".join(observation.errors[:20]))
        return "\n".join(parts)

    if observation.kind == "python_call_graph":
        parts = [
            (
                f"{index}. python_call_graph {observation.path or '.'}: {observation.message} "
                f"truncated={str(observation.truncated).lower()}"
            )
        ]
        for edge in observation.edges[:160]:
            parts.append(
                (
                    f"{edge.path}:{edge.line}:{edge.column}: "
                    f"caller={edge.caller or '.'} callee={edge.callee} {edge.context}"
                )
            )
        if observation.errors:
            parts.append("errors:\n" + "\n".join(observation.errors[:20]))
        return "\n".join(parts)

    if observation.kind == "python_references":
        parts = [
            (
                f"{index}. python_references {observation.symbol}: {observation.message} "
                f"path={observation.path or '.'} truncated={str(observation.truncated).lower()}"
            )
        ]
        for reference in observation.references[:160]:
            parts.append(
                (
                    f"{reference.path}:{reference.line}:{reference.column}: "
                    f"{reference.kind} {reference.context}"
                )
            )
        if observation.errors:
            parts.append("errors:\n" + "\n".join(observation.errors[:20]))
        return "\n".join(parts)

    if observation.kind == "python_reference_contexts":
        parts = [
            (
                f"{index}. python_reference_contexts {observation.symbol}: {observation.message} "
                f"shown={len(observation.contexts)}/{observation.total} "
                f"path={observation.path or '.'} "
                f"context_lines={observation.context_lines} "
                f"truncated={str(observation.truncated).lower()}"
            )
        ]
        for context in observation.contexts[:80]:
            parts.append(
                (
                    f"reference: {context.path}:{context.line}:{context.column} "
                    f"kind={context.kind} range={context.start_line}-{context.end_line} "
                    f"truncated={str(context.truncated).lower()} "
                    f"match={context.matched_line}"
                )
            )
            parts.append("content:\n" + truncate(context.content))
        if observation.errors:
            parts.append("errors:\n" + "\n".join(observation.errors[:20]))
        return "\n".join(parts)

    if observation.kind == "python_rename_preview":
        parts = [
            (
                f"{index}. python_rename_preview {observation.symbol}->{observation.new_name}: "
                f"{observation.message} path={observation.path or '.'} "
                f"files={len(observation.files)}/{observation.total_files} "
                f"replacements={observation.total_replacements} "
                f"truncated={str(observation.truncated).lower()}"
            )
        ]
        for file in observation.files[:40]:
            parts.append(
                (
                    f"file: {file.path} replacements={len(file.replacements)} "
                    f"truncated={str(file.truncated).lower()}"
                )
            )
            for replacement in file.replacements[:80]:
                parts.append(
                    (
                        f"replace: {replacement.path}:{replacement.line}:{replacement.column}-"
                        f"{replacement.end_column} kind={replacement.kind} "
                        f"{replacement.old}->{replacement.new} {replacement.context}"
                    )
                )
            parts.append(f"diff:\n{truncate(file.diff)}")
        if observation.errors:
            parts.append("errors:\n" + "\n".join(observation.errors[:20]))
        return "\n".join(parts)

    if observation.kind == "python_rename":
        parts = [
            (
                f"{index}. python_rename {observation.symbol}->{observation.new_name}: "
                f"{observation.message} path={observation.path or '.'} "
                f"files={len(observation.files)}/{observation.total_files} "
                f"replacements={observation.total_replacements}"
            )
        ]
        for file in observation.files[:40]:
            parts.append(f"file: {file.path} replacements={len(file.replacements)}")
        if observation.diff:
            parts.append(f"diff:\n{truncate(observation.diff)}")
        if observation.errors:
            parts.append("errors:\n" + "\n".join(observation.errors[:20]))
        return "\n".join(parts)

    return None
