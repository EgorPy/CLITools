""" Project structure extractor """

from __future__ import annotations

import argparse
import json
import os
import sys

DEFAULT_EXTENSIONS = {".py", ".js", ".ts", ".html", ".css", ".yaml", ".yml", ".json"}
DEFAULT_IGNORE = {"venv", ".venv", ".git", "__pycache__", "node_modules", ".idea", ".vscode", "build", "dist"}


def extract_project_structure(
    root_path: str,
    extensions: set[str] | None = None,
    ignore_folders: set[str] | None = None,
) -> dict:
    if extensions is None:
        extensions = DEFAULT_EXTENSIONS
    if ignore_folders is None:
        ignore_folders = DEFAULT_IGNORE

    def scan_dir(path: str) -> dict | None:
        files: list[str] = []
        folders: dict[str, dict] = {}

        try:
            entries = os.listdir(path)
        except (PermissionError, OSError):
            return None

        for entry in entries:
            if entry in ignore_folders:
                continue
            full_path = os.path.join(path, entry)
            if os.path.isfile(full_path):
                if os.path.splitext(entry)[1] in extensions:
                    files.append(entry)
            elif os.path.isdir(full_path):
                sub = scan_dir(full_path)
                if sub:
                    folders[entry] = sub

        if not files and not folders:
            return None

        result: dict = {}
        if files:
            result["files"] = sorted(files)
        for name in sorted(folders):
            result[name] = folders[name]
        return result

    if not os.path.isdir(root_path):
        return {}

    return scan_dir(root_path) or {}


def render_tree(structure: dict, prefix: str = "") -> str:
    lines: list[str] = []
    entries = list(structure.items())
    for i, (name, value) in enumerate(entries):
        is_last = i == len(entries) - 1
        connector = "└── " if is_last else "├── "
        lines.append(f"{prefix}{connector}{name}")

        if isinstance(value, dict):
            new_prefix = prefix + ("    " if is_last else "│   ")
            lines.append(render_tree(value, new_prefix).rstrip("\n"))
        elif isinstance(value, list):
            for j, f in enumerate(value):
                sub_last = j == len(value) - 1
                sub_connector = "└── " if sub_last else "├── "
                lines.append(f"{prefix}{'    ' if is_last else '│   '}{sub_connector}{f}")

    return "\n".join(line for line in lines if line)


def _normalize_extensions(raw: list[str] | None) -> set[str] | None:
    if not raw:
        return None
    result = set()
    for ext in raw:
        ext = ext.strip().lower()
        if not ext:
            continue
        if not ext.startswith("."):
            ext = "." + ext
        result.add(ext)
    return result or None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="project-structure",
        description="Extract project structure as JSON or a text tree.",
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Root folder of the project (default: current directory).",
    )
    parser.add_argument(
        "-e", "--extensions",
        nargs="*",
        default=None,
        help="File extensions to include.",
    )
    parser.add_argument(
        "-i", "--ignore",
        nargs="*",
        default=None,
        help="Folders to ignore (extends the default set).",
    )
    parser.add_argument(
        "-f", "--format",
        choices=("json", "tree"),
        default="json",
        help="Output format (default: json).",
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="File to save the result to (otherwise stdout).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    extensions = _normalize_extensions(args.extensions)
    ignore = set(DEFAULT_IGNORE)
    if args.ignore:
        ignore.update(args.ignore)

    structure = extract_project_structure(args.path, extensions, ignore)

    if args.format == "json":
        rendered = json.dumps(structure, indent=2, ensure_ascii=False)
    else:
        root_name = os.path.basename(os.path.abspath(args.path)) or args.path
        rendered = f"{root_name}/\n{render_tree(structure)}"

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(rendered)
        print(f"Saved to {args.output}", file=sys.stderr)
    else:
        print(rendered)

    return 0


if __name__ == "__main__":
    sys.exit(main())