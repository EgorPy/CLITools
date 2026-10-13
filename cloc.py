from __future__ import annotations

import argparse
import os
import sys

from core.logger import logger

DEFAULT_IGNORE_FOLDERS = {
    "venv", ".venv", ".git", "__pycache__",
    ".idea", ".vscode", "build", "dist", "node_modules",
    ".cache", ".codex", ".gradle", ".android", ".docker"
}

DEFAULT_EXTENSIONS = {
    ".py", ".pyi",
    ".js", ".jsx", ".mjs", ".cjs",
    ".ts", ".tsx",
    ".html", ".htm", ".css", ".scss", ".sass", ".less",
    ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg",
    ".md", ".rst", ".txt",
    ".sh", ".bash", ".zsh", ".bat", ".cmd", ".ps1",
    ".c", ".h", ".cpp", ".hpp", ".cc", ".hh",
    ".cs", ".java", ".kt", ".go", ".rs", ".rb", ".php",
    ".sql", ".graphql", ".proto",
    ".xml", ".svg",
}

ENCODINGS = ("utf-8", "utf-8-sig", "cp1251", "cp866", "latin-1")

VERBOSE_WIDTH = 60
NUMBER_WIDTH = 10


def _fmt_number(n: int) -> str:
    return f"{n:>{NUMBER_WIDTH}}"


def _format_verbose_line(path: str, lines: int) -> str:
    return f"{_fmt_number(lines)}  {path}"


def count_lines_in_file(filename: str, encoding: str | None = None) -> int:
    encodings = (encoding,) if encoding else ENCODINGS

    content: str | None = None
    for enc in encodings:
        try:
            with open(filename, "r", encoding=enc) as file:
                content = file.read()
            break
        except (UnicodeDecodeError, LookupError):
            continue
        except (PermissionError, OSError):
            return 0

    if content is None:
        try:
            with open(filename, "rb") as file:
                data = file.read()
        except (PermissionError, OSError):
            return 0
        if not data:
            return 0
        count = data.count(b"\n")
        if not data.endswith(b"\n"):
            count += 1
        return count

    if not content:
        return 0

    count = content.count("\n")
    if not content.endswith("\n"):
        count += 1
    return count


def is_extension_allowed(filename: str, extensions: set[str] | None) -> bool:
    if not extensions:
        return True
    extension = os.path.splitext(filename)[1].lower()
    return extension in extensions


def count_lines_in_folder(
        path: str,
        recursive: bool = False,
        extensions: set[str] | None = None,
        ignore_folders: set[str] | None = None,
        verbose: bool = False,
        encoding: str | None = None,
) -> tuple[int, int]:
    if ignore_folders is None:
        ignore_folders = DEFAULT_IGNORE_FOLDERS
    if extensions is None:
        extensions = DEFAULT_EXTENSIONS

    if os.path.isfile(path):
        if not is_extension_allowed(path, extensions):
            return 0, 0
        lines = count_lines_in_file(path, encoding)
        if verbose:
            logger.info(_format_verbose_line(path, lines))
        return lines, 1

    if not os.path.isdir(path):
        logger.error(f"Path not found: {path}")
        return 0, 0

    total = 0
    files = 0

    if recursive:
        for root, dirs, filenames in os.walk(path):
            dirs[:] = [d for d in dirs if d not in ignore_folders]
            for name in filenames:
                full = os.path.join(root, name)
                if not is_extension_allowed(full, extensions):
                    continue
                lines = count_lines_in_file(full, encoding)
                if verbose:
                    logger.info(_format_verbose_line(full, lines))
                total += lines
                files += 1
    else:
        for name in os.listdir(path):
            full = os.path.join(path, name)
            if os.path.isdir(full):
                continue
            if not is_extension_allowed(full, extensions):
                continue
            lines = count_lines_in_file(full, encoding)
            if verbose:
                logger.info(_format_verbose_line(full, lines))
            total += lines
            files += 1

    return total, files


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
        prog="cloc",
        description="Count lines of code in project files.",
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="File or folder to analyze (default: current directory).",
    )
    parser.add_argument(
        "-r", "--recursive",
        action="store_true",
        help="Recursively scan nested folders.",
    )
    parser.add_argument(
        "-e", "--extensions",
        nargs="*",
        default=None,
        help="Override the default extension whitelist (e.g. .py .js .html).",
    )
    parser.add_argument(
        "-a", "--all",
        action="store_true",
        help="Disable the whitelist and count every file.",
    )
    parser.add_argument(
        "-i", "--ignore",
        nargs="*",
        default=None,
        help="Folders to ignore (extends the default set).",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Print line count for each file.",
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Do not print the summary line.",
    )
    parser.add_argument(
        "--encoding",
        default=None,
        help="Force a specific encoding (e.g. cp1251).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.all:
        extensions: set[str] | None = None
    elif args.extensions is not None:
        extensions = _normalize_extensions(args.extensions)
    else:
        extensions = DEFAULT_EXTENSIONS

    ignore_folders = set(DEFAULT_IGNORE_FOLDERS)
    if args.ignore:
        ignore_folders.update(args.ignore)

    total, files = count_lines_in_folder(
        path=args.path,
        recursive=args.recursive,
        extensions=extensions,
        ignore_folders=ignore_folders,
        verbose=args.verbose,
        encoding=args.encoding,
    )

    if not args.quiet:
        if args.verbose:
            logger.info("-" * VERBOSE_WIDTH)
        logger.info(f"{_fmt_number(total)}  Total ({files} files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
