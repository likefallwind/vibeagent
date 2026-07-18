"""Python implementation of VibeAgent."""

# Public metadata for package consumers and tooling.
__all__ = ["MACHINE_OUTPUT_SCHEMA_VERSION", "__version__"]

# Keep a stable project version for package/runtime checks.
__version__ = "1.0.0"

# Increment only when machine-readable JSON output makes a breaking contract change.
MACHINE_OUTPUT_SCHEMA_VERSION = 1
