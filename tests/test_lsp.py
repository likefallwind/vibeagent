import json
import tempfile
import unittest
from pathlib import Path

from vibeagent.agent import run_agent
from vibeagent.actions import AGENT_TOOL_DEFINITIONS, execute_action, parse_tool_action
from vibeagent.action_tool_aliases import profile_tool_names, tool_name_candidates
from vibeagent.tool_catalog_core import tool_category, tool_name_requires_approval
from vibeagent.types import AssistantResponse, ChatMessage, ContentBlock, LspQueryAction
from vibeagent.workspace import create_run_workspace


class LspAgentClient:
    def __init__(self, responses: list[list[ContentBlock]]) -> None:
        self.responses = responses
        self.messages: list[list[ChatMessage]] = []
        self.tools: list[list[dict]] = []

    def complete(self, messages, tools=None, max_tokens=4096, temperature=0.2, timeout_ms=120_000):
        self.messages.append(list(messages))
        self.tools.append(list(tools or []))
        content = self.responses[len(self.messages) - 1]
        return AssistantResponse(content=content, raw={"content": content})


class LspCompatibilityTests(unittest.TestCase):
    def test_lsp_alias_parses_claude_fields_and_is_read_only(self) -> None:
        action = parse_tool_action(
            "LSP",
            {
                "operation": "goToDefinition",
                "filePath": "src/app.ts",
                "line": 4,
                "character": 8,
                "maxResults": 7,
            },
        )

        self.assertEqual(
            action,
            LspQueryAction(
                type="lsp_query",
                operation="goToDefinition",
                path="src/app.ts",
                line=4,
                character=8,
                max_results=7,
            ),
        )
        self.assertIn("LSP", tool_name_candidates("lsp_query", action))
        self.assertEqual(profile_tool_names("LSP"), frozenset({"LSP", "lsp_query"}))
        self.assertFalse(tool_name_requires_approval("LSP"))
        self.assertEqual(tool_category("LSP"), "project")
        self.assertIn("LSP", {tool["name"] for tool in AGENT_TOOL_DEFINITIONS})

    def test_lsp_finds_typescript_definition_from_position(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-lsp-") as base:
            root = Path(base)
            (root / "src").mkdir()
            (root / "src" / "app.ts").write_text(
                "function greet(name: string) {\n  return name;\n}\nconsole.log(greet('Ada'));\n",
                encoding="utf-8",
            )
            workspace = create_run_workspace(root, "run-1")
            observation = execute_action(
                workspace,
                parse_tool_action(
                    "LSP",
                    {"operation": "goToDefinition", "filePath": "src/app.ts", "line": 4, "character": 14},
                ),
            )

        self.assertEqual(observation.kind, "code_definitions")
        self.assertTrue(observation.ok)
        self.assertEqual(observation.symbol, "greet")
        self.assertEqual(observation.definitions[0].line, 1)

    def test_lsp_finds_python_references_with_utf16_character_offset(self) -> None:
        call_line = 'print("😀", greet("Ada"))'
        prefix = call_line[: call_line.index("greet")]
        utf16_offset = len(prefix.encode("utf-16-le")) // 2
        with tempfile.TemporaryDirectory(prefix="vibeagent-lsp-") as base:
            root = Path(base)
            (root / "app.py").write_text(
                "def greet(name):\n    return name\n\n" + call_line + "\n",
                encoding="utf-8",
            )
            workspace = create_run_workspace(root, "run-1")
            observation = execute_action(
                workspace,
                parse_tool_action(
                    "LSP",
                    {
                        "operation": "findReferences",
                        "filePath": "app.py",
                        "line": 4,
                        "character": utf16_offset,
                    },
                ),
            )

        self.assertEqual(observation.kind, "python_references")
        self.assertTrue(observation.ok)
        self.assertEqual(observation.symbol, "greet")
        self.assertEqual(observation.total, 2)

    def test_lsp_document_symbols_and_invalid_positions_are_bounded(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-lsp-") as base:
            root = Path(base)
            (root / "app.py").write_text("def greet():\n    return 'hi'\n", encoding="utf-8")
            workspace = create_run_workspace(root, "run-1")
            symbols = execute_action(
                workspace,
                parse_tool_action("LSP", {"operation": "documentSymbol", "filePath": "app.py"}),
            )
            invalid = execute_action(
                workspace,
                parse_tool_action(
                    "LSP", {"operation": "hover", "filePath": "app.py", "line": 99, "character": 1}
                ),
            )

        self.assertEqual(symbols.kind, "code_outline")
        self.assertEqual(symbols.files[0].symbols[0].name, "greet")
        self.assertEqual(invalid.kind, "tool_error")
        self.assertIn("outside app.py", invalid.message)

    def test_agent_discovers_lsp_then_uses_definition_result(self) -> None:
        client = LspAgentClient(
            [
                [
                    {
                        "type": "tool_call",
                        "id": "search-1",
                        "name": "ToolSearch",
                        "input": {"query": "LSP", "max_matches": 3},
                    }
                ],
                [
                    {
                        "type": "tool_call",
                        "id": "lsp-1",
                        "name": "LSP",
                        "input": {
                            "operation": "goToDefinition",
                            "filePath": "src/app.ts",
                            "line": 4,
                            "character": 14,
                        },
                    }
                ],
                [{"type": "text", "text": "greet is defined on line 1."}],
            ]
        )

        with tempfile.TemporaryDirectory(prefix="vibeagent-lsp-agent-") as base:
            root = Path(base)
            (root / "src").mkdir()
            (root / "src" / "app.ts").write_text(
                "function greet(name: string) {\n  return name;\n}\nconsole.log(greet('Ada'));\n",
                encoding="utf-8",
            )
            result = run_agent("Find the definition at the call site", base_dir=root, client=client, max_iterations=3)

        first_names = {str(tool["name"]) for tool in client.tools[0]}
        second_names = {str(tool["name"]) for tool in client.tools[1]}
        lsp_result = json.loads(client.messages[2][-1].content[0]["content"])
        self.assertTrue(result.success)
        self.assertEqual([observation.kind for observation in result.observations], ["tool_search", "code_definitions"])
        self.assertNotIn("LSP", first_names)
        self.assertIn("LSP", second_names)
        self.assertEqual(lsp_result["symbol"], "greet")
        self.assertEqual(lsp_result["definitions"][0]["line"], 1)


if __name__ == "__main__":
    unittest.main()
