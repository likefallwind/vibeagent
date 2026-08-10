from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import patch


class IsolatedUserHomeTestCase(unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()
        self._user_home = tempfile.TemporaryDirectory(prefix="vibeagent-test-user-home-")
        self._user_home_environment = patch.dict(
            os.environ,
            {"VIBEAGENT_USER_HOME": self._user_home.name},
        )
        self._user_home_environment.start()

    def tearDown(self) -> None:
        self._user_home_environment.stop()
        self._user_home.cleanup()
        super().tearDown()


__all__ = ["IsolatedUserHomeTestCase"]
