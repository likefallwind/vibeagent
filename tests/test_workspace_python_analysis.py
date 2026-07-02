import ast
import unittest

from vibeagent import workspace_code_intel, workspace_python_analysis, workspace_python_intel


class WorkspacePythonAnalysisTests(unittest.TestCase):
    def test_python_intel_and_code_intel_reexport_analysis_helpers(self) -> None:
        names = [
            "check_python_syntax",
            "check_python_file_paths",
            "inspect_python_dependencies",
            "build_python_module_index",
            "module_name_for_python_path",
            "collect_python_dependency_imports",
            "resolve_import_from_module",
            "resolve_import_target",
            "is_local_python_module",
            "python_import_sort_key",
        ]
        for name in names:
            with self.subTest(name=name):
                self.assertIs(getattr(workspace_python_intel, name), getattr(workspace_python_analysis, name))
                self.assertIs(getattr(workspace_code_intel, name), getattr(workspace_python_analysis, name))

    def test_module_index_and_import_collection_classify_local_imports(self) -> None:
        local_modules = workspace_python_analysis.build_python_module_index(
            [
                "pkg/__init__.py",
                "pkg/service.py",
                "pkg/utils/helpers.py",
                "tests/test_service.py",
            ]
        )
        tree = ast.parse("import os\nfrom .utils import helpers\nfrom pkg import service as svc\n")

        imports = workspace_python_analysis.collect_python_dependency_imports(
            tree,
            current_module="pkg.service",
            local_modules=local_modules,
            max_imports=10,
        )

        self.assertIn("pkg", local_modules)
        self.assertIn("pkg.utils.helpers", local_modules)
        self.assertEqual(workspace_python_analysis.module_name_for_python_path("pkg/__init__.py"), "pkg")
        self.assertEqual(workspace_python_analysis.resolve_import_from_module("pkg.service", 1, "utils"), "pkg.utils")
        self.assertEqual(workspace_python_analysis.resolve_import_target("pkg", "service", local_modules), "pkg.service")
        self.assertEqual([item["target"] for item in imports], ["os", "pkg.utils.helpers", "pkg.service"])
        self.assertEqual([item["local"] for item in imports], [False, True, True])


if __name__ == "__main__":
    unittest.main()
