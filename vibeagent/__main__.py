"""CLI entrypoint module for launching VibeAgent."""

from .cli import main

# `main()` returns an int exit status; convert directly to process exit.
raise SystemExit(main())
