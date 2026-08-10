from __future__ import annotations

import os
import tempfile


_TEST_USER_HOME = tempfile.TemporaryDirectory(prefix="vibeagent-suite-user-home-")
os.environ.setdefault("VIBEAGENT_USER_HOME", _TEST_USER_HOME.name)
