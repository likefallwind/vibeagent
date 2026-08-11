from __future__ import annotations

import argparse
import json
from pathlib import Path
import zipfile


ROOT = Path(__file__).resolve().parents[1]
EXTENSION_ROOT = ROOT / "extensions" / "vscode"
SOURCE_FILES = (
    "package.json",
    "extension.js",
    "README.md",
    "src/core.js",
    "src/context.js",
    "src/remote.js",
    "src/agentChanges.js",
    "src/agentPanel.js",
    "src/agentPanelView.js",
    "src/localCli.js",
    "src/sessionCatalog.js",
    "src/sessionInspectorClient.js",
    "src/sessionInspector.js",
    "src/sessionInspectorView.js",
    "src/sessionPlan.js",
    "src/sessionRewindClient.js",
    "src/sessionRewind.js",
    "src/terminals.js",
)
ZIP_TIMESTAMP = (2024, 1, 1, 0, 0, 0)


def build_extension(output: Path) -> Path:
    manifest = _read_manifest()
    version = manifest["version"]
    publisher = manifest["publisher"]
    name = manifest["name"]
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}.tmp")
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            _write_text(archive, "[Content_Types].xml", _content_types())
            _write_text(
                archive,
                "extension.vsixmanifest",
                _vsix_manifest(name=name, version=version, publisher=publisher, display_name=manifest["displayName"]),
            )
            for relative in SOURCE_FILES:
                source = EXTENSION_ROOT / relative
                if not source.is_file() or source.is_symlink():
                    raise ValueError(f"VS Code extension source must be a regular file: {source}")
                _write_bytes(archive, f"extension/{relative}", source.read_bytes())
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)
    return output


def default_output() -> Path:
    manifest = _read_manifest()
    return ROOT / "dist" / f"{manifest['name']}-{manifest['version']}.vsix"


def _read_manifest() -> dict[str, object]:
    path = EXTENSION_ROOT / "package.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    string_fields = ("name", "displayName", "version", "publisher", "main")
    object_fields = ("engines", "contributes")
    if not isinstance(payload, dict):
        raise ValueError("VS Code extension package.json must be an object.")
    if any(not isinstance(payload.get(key), str) or not payload[key] for key in string_fields):
        raise ValueError("VS Code extension package.json is missing required text fields.")
    if any(not isinstance(payload.get(key), dict) for key in object_fields):
        raise ValueError("VS Code extension package.json is missing required fields.")
    if payload.get("main") != "./extension.js":
        raise ValueError("VS Code extension main must be ./extension.js.")
    return payload


def _write_text(archive: zipfile.ZipFile, name: str, value: str) -> None:
    _write_bytes(archive, name, value.encode("utf-8"))


def _write_bytes(archive: zipfile.ZipFile, name: str, value: bytes) -> None:
    info = zipfile.ZipInfo(name, ZIP_TIMESTAMP)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    archive.writestr(info, value)


def _content_types() -> str:
    return """<?xml version="1.0" encoding="utf-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="json" ContentType="application/json" />
  <Default Extension="js" ContentType="application/javascript" />
  <Default Extension="md" ContentType="text/markdown" />
  <Override PartName="/extension.vsixmanifest" ContentType="text/xml" />
</Types>
"""


def _vsix_manifest(*, name: str, version: str, publisher: str, display_name: str) -> str:
    values = (name, version, publisher, display_name)
    if any(not isinstance(value, str) or not value or any(char in value for char in '<>&"') for value in values):
        raise ValueError("VSIX identity fields must be non-empty XML-safe text.")
    return f"""<?xml version="1.0" encoding="utf-8"?>
<PackageManifest Version="2.0.0" xmlns="http://schemas.microsoft.com/developer/vsx-schema/2011">
  <Metadata>
    <Identity Language="en-US" Id="{name}" Version="{version}" Publisher="{publisher}" />
    <DisplayName>{display_name}</DisplayName>
    <Description xml:space="preserve">VibeAgent terminal and editor integration for VS Code.</Description>
    <Tags>agent,coding,ai</Tags>
    <Categories>Other,Machine Learning</Categories>
    <Properties>
      <Property Id="Microsoft.VisualStudio.Code.Engine" Value="^1.98.0" />
      <Property Id="Microsoft.VisualStudio.Code.ExtensionKind" Value="workspace" />
      <Property Id="Microsoft.VisualStudio.Code.ExtensionUntrustedWorkspaces" Value="supported" />
      <Property Id="Microsoft.VisualStudio.Services.Content.Pricing" Value="Free" />
    </Properties>
  </Metadata>
  <Installation>
    <InstallationTarget Id="Microsoft.VisualStudio.Code" />
  </Installation>
  <Dependencies />
  <Assets>
    <Asset Type="Microsoft.VisualStudio.Code.Manifest" Path="extension/package.json" Addressable="true" />
    <Asset Type="Microsoft.VisualStudio.Services.Content.Details" Path="extension/README.md" Addressable="true" />
  </Assets>
</PackageManifest>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the dependency-free VibeAgent VS Code extension VSIX.")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    output = build_extension(args.output or default_output())
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
