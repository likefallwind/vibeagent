from __future__ import annotations

import unittest

from vibeagent import workspace_path_discovery, workspace_search, workspace_tree_ignore


class WorkspacePathDiscoveryTests(unittest.TestCase):
    def test_workspace_search_reexports_path_discovery_helpers(self) -> None:
        self.assertIs(workspace_search.find_project_files_result, workspace_path_discovery.find_project_files_result)
        self.assertIs(workspace_search.glob_project_files, workspace_path_discovery.glob_project_files)
        self.assertIs(workspace_search.validate_glob_pattern, workspace_path_discovery.validate_glob_pattern)
        self.assertIs(workspace_search.list_project_files, workspace_path_discovery.list_project_files)
        self.assertIs(workspace_search.list_project_tree, workspace_path_discovery.list_project_tree)
        self.assertIs(workspace_search.normalize_list_tree_ignore, workspace_path_discovery.normalize_list_tree_ignore)
        self.assertIs(workspace_search.list_tree_entry_matches_ignore, workspace_path_discovery.list_tree_entry_matches_ignore)
        self.assertIs(workspace_search.build_repo_map, workspace_path_discovery.build_repo_map)

    def test_path_discovery_reexports_tree_ignore_helpers(self) -> None:
        self.assertIs(workspace_path_discovery.normalize_list_tree_ignore, workspace_tree_ignore.normalize_list_tree_ignore)
        self.assertIs(workspace_path_discovery.list_tree_entry_matches_ignore, workspace_tree_ignore.list_tree_entry_matches_ignore)

    def test_tree_ignore_helpers_normalize_and_match_patterns(self) -> None:
        ignore = workspace_tree_ignore.normalize_list_tree_ignore((" generated\\** ", "*.log"))

        self.assertEqual(ignore, ("generated/**", "*.log"))
        self.assertTrue(workspace_tree_ignore.list_tree_entry_matches_ignore("generated/out.py", ignore))
        self.assertTrue(workspace_tree_ignore.list_tree_entry_matches_ignore("src/debug.log", ignore))
        self.assertFalse(workspace_tree_ignore.list_tree_entry_matches_ignore("src/app.py", ignore))


if __name__ == "__main__":
    unittest.main()
