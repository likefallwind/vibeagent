from __future__ import annotations


DEFECT_REVIEW_PERSPECTIVES = ("correctness", "security", "tests")
CLEANUP_REVIEW_PERSPECTIVES = ("reuse", "simplicity", "efficiency", "abstraction")
SECURITY_REVIEW_PERSPECTIVES = ("access_control", "injection", "data_exposure", "supply_chain")
REVIEW_PERSPECTIVES = {
    "defects": DEFECT_REVIEW_PERSPECTIVES,
    "cleanup": CLEANUP_REVIEW_PERSPECTIVES,
    "security": SECURITY_REVIEW_PERSPECTIVES,
}

PERSPECTIVE_GUIDANCE = {
    "correctness": (
        "Trace changed behavior through callers and contracts. Look for logic errors, regressions, "
        "broken edge cases, state inconsistencies, and incorrect error handling."
    ),
    "security": (
        "Inspect changed trust boundaries. Look for authorization mistakes, injection, unsafe path or "
        "command handling, secret exposure, insecure defaults, and validation bypasses."
    ),
    "tests": (
        "Assess whether tests exercise the changed behavior and likely failure modes. Report missing or "
        "misleading coverage only when it can hide a concrete regression; do not request coverage for its own sake."
    ),
    "reuse": (
        "Look for new code that duplicates an existing helper, utility, component, abstraction, or established "
        "repository pattern. Recommend reuse only after locating and inspecting the concrete existing alternative."
    ),
    "simplicity": (
        "Look for unnecessary branching, indirection, state, configuration, or custom machinery in changed code. "
        "Prefer the smallest behavior-preserving implementation that remains clear at the call site."
    ),
    "efficiency": (
        "Look for concrete avoidable work in changed code, such as repeated I/O, redundant parsing, unbounded scans, "
        "or needless allocation. Reject speculative micro-optimizations without an identifiable workload impact."
    ),
    "abstraction": (
        "Check whether changed behavior lives at the correct ownership boundary and abstraction level. Flag leaky, "
        "premature, or misplaced abstractions only when a specific simpler repository-aligned placement is evident."
    ),
    "access_control": (
        "Trace authentication, authorization, tenancy, ownership, privilege transitions, and fail-open behavior across "
        "changed trust boundaries. Require a concrete path by which an actor gains access beyond their intended rights."
    ),
    "injection": (
        "Trace attacker-controlled input into command, query, template, path, parser, deserialization, URL-fetch, or "
        "code-execution sinks. Verify the actual escaping, validation, canonicalization, and execution context."
    ),
    "data_exposure": (
        "Inspect changed storage, logging, errors, serialization, network responses, and secret handling for unauthorized "
        "disclosure or integrity loss. Identify the sensitive asset, unauthorized observer, and exposure path."
    ),
    "supply_chain": (
        "Inspect changed dependencies, build/release inputs, configuration, cryptography, update paths, and insecure defaults. "
        "Report only risks with a concrete untrusted input, compromised boundary, or unsafe production consequence."
    ),
}


__all__ = [
    "CLEANUP_REVIEW_PERSPECTIVES",
    "DEFECT_REVIEW_PERSPECTIVES",
    "PERSPECTIVE_GUIDANCE",
    "REVIEW_PERSPECTIVES",
    "SECURITY_REVIEW_PERSPECTIVES",
]
