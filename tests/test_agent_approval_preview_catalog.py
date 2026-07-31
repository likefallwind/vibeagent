from __future__ import annotations

import unittest

import vibeagent.agent_approval_preview_catalog as preview_catalog
from vibeagent.actions import AGENT_TOOL_DEFINITIONS
from vibeagent.commands import APPROVAL_REQUIRED_TOOL_NAMES


class ApprovalPreviewCatalogTests(unittest.TestCase):
    def test_mapping_covers_approval_required_tools(self) -> None:
        tool_names = {tool["name"] for tool in AGENT_TOOL_DEFINITIONS}
        missing = sorted(
            APPROVAL_REQUIRED_TOOL_NAMES
            - set(preview_catalog.PREVIEW_KIND_BY_ACTION_TYPE)
            - preview_catalog.APPROVAL_WITHOUT_PREVIEW_ACTION_TYPES
        )
        invalid = sorted(
            (action_name, preview_name)
            for action_name, preview_name in preview_catalog.PREVIEW_KIND_BY_ACTION_TYPE.items()
            if action_name in APPROVAL_REQUIRED_TOOL_NAMES and preview_name not in tool_names
        )

        self.assertEqual(missing, [])
        self.assertEqual(invalid, [])


if __name__ == "__main__":
    unittest.main()
