"""CLI entrypoint module for launching VibeAgent."""

import sys

from .cli import main

# `main()` returns an int exit status; convert directly to process exit.
raise SystemExit(main(sys.argv[1:]))
