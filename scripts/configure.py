#!/usr/bin/env python3
"""Install or remove GlyphTap's optional Omarchy menu and keybinding entries."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import tempfile


PLUGIN_ID = "io.github.juancamilogra.glyphtap"
COMMAND = f"omarchy-shell shell toggle {PLUGIN_ID}"
BINDING_START = "-- GLYPHTAP MANAGED BINDING START"
BINDING_END = "-- GLYPHTAP MANAGED BINDING END"
MENU_START = "// GLYPHTAP MANAGED MENU START"
MENU_END = "// GLYPHTAP MANAGED MENU END"


class ConfigError(RuntimeError):
    pass


def config_home() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))


def atomic_write(path: Path, content: str, mode: int | None = None) -> None:
    path.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
    if path.is_symlink():
        raise ConfigError(f"Refusing to replace symlinked config: {path}")
    existing_mode = path.stat().st_mode & 0o777 if path.exists() else (mode or 0o644)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.glyphtap.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, existing_mode)
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def remove_marked(content: str, start: str, end: str) -> str:
    starts = [match.start() for match in re.finditer(re.escape(start), content)]
    ends = [match.end() for match in re.finditer(re.escape(end), content)]
    if not starts and not ends:
        return content
    if len(starts) != 1 or len(ends) != 1 or starts[0] >= ends[0]:
        raise ConfigError(f"Managed block markers are malformed: {start}")
    begin = content.rfind("\n", 0, starts[0]) + 1
    finish = content.find("\n", ends[0])
    finish = len(content) if finish < 0 else finish + 1
    return content[:begin] + content[finish:]


def strip_jsonc(value: str) -> str:
    out: list[str] = []
    index = 0
    quote = ""
    escaped = False
    while index < len(value):
        char = value[index]
        next_char = value[index + 1] if index + 1 < len(value) else ""
        if quote:
            out.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = ""
            index += 1
        elif char in ('"', "'"):
            quote = char
            out.append(char)
            index += 1
        elif char == "/" and next_char == "/":
            index += 2
            while index < len(value) and value[index] != "\n":
                index += 1
        elif char == "/" and next_char == "*":
            index += 2
            while index + 1 < len(value) and value[index : index + 2] != "*/":
                index += 1
            index += 2
        else:
            out.append(char)
            index += 1
    return "".join(out)


def root_close_index(content: str) -> int:
    clean = strip_jsonc(content)
    if not clean.strip().startswith("{") or not clean.strip().endswith("}"):
        raise ConfigError("Omarchy menu extension is not a root JSONC object")
    # The last brace is safe because comments and strings were removed only for
    # validation; find the last real brace in the original with the same lexer.
    quote = ""
    escaped = False
    line_comment = False
    block_comment = False
    candidate = -1
    index = 0
    while index < len(content):
        char = content[index]
        nxt = content[index + 1] if index + 1 < len(content) else ""
        if line_comment:
            if char == "\n": line_comment = False
        elif block_comment:
            if char == "*" and nxt == "/": block_comment = False; index += 1
        elif quote:
            if escaped: escaped = False
            elif char == "\\": escaped = True
            elif char == quote: quote = ""
        elif char in ('"', "'"):
            quote = char
        elif char == "/" and nxt == "/":
            line_comment = True; index += 1
        elif char == "/" and nxt == "*":
            block_comment = True; index += 1
        elif char == "}":
            candidate = index
        index += 1
    if candidate < 0:
        raise ConfigError("Omarchy menu extension has no closing object brace")
    return candidate


def install_binding(content: str, force: bool) -> str:
    content = remove_marked(content, BINDING_START, BINDING_END)
    if re.search(r"SUPER\s*\+\s*I", content, re.IGNORECASE) and not force:
        raise ConfigError("SUPER + I is already mentioned in bindings.lua; rerun with --force to add GlyphTap anyway")
    block = (
        f"{BINDING_START}\n"
        f'o.bind("SUPER + I", "GlyphTap", "{COMMAND}")\n'
        f"{BINDING_END}\n"
    )
    separator = "" if not content or content.endswith("\n") else "\n"
    return content + separator + block


def install_menu(content: str) -> str:
    content = remove_marked(content, MENU_START, MENU_END)
    if re.search(r'["\']glyphtap["\']\s*:', strip_jsonc(content), re.IGNORECASE):
        raise ConfigError("A non-managed 'glyphtap' menu entry already exists")
    close = root_close_index(content)
    before = content[:close]
    after = content[close:]
    significant = strip_jsonc(before).rstrip()
    needs_comma = significant not in ("", "{") and not significant.endswith(",")
    prefix = "," if needs_comma else ""
    block = (
        f"\n  {MENU_START}\n"
        f'  {prefix}"glyphtap": {{"icon":"󰋇","label":"GlyphTap","description":"Search icons and copy SVGs","action":"{COMMAND}","aliases":["icons","svg"]}}\n'
        f"  {MENU_END}\n"
    )
    return before.rstrip() + block + after.lstrip()


def remove_menu(content: str) -> str:
    had_marker = MENU_START in content or MENU_END in content
    content = remove_marked(content, MENU_START, MENU_END)
    if not had_marker:
        return content
    # The install block owns its leading separator. If the object was empty at
    # install time and a later property was appended, consume that property's
    # leading comma so uninstall still leaves valid JSONC.
    open_index = content.find("{")
    close_index = root_close_index(content)
    body = content[open_index + 1 : close_index]
    clean = strip_jsonc(body).lstrip()
    if clean.startswith(","):
        absolute = open_index + 1
        while absolute < close_index:
            if content[absolute] == ",":
                content = content[:absolute] + content[absolute + 1 :]
                break
            absolute += 1
    return content


def configure(action: str, force: bool = False) -> list[Path]:
    binding_path = config_home() / "hypr" / "bindings.lua"
    menu_path = config_home() / "omarchy" / "extensions" / "omarchy-menu.jsonc"
    binding_original = binding_path.read_text(encoding="utf-8") if binding_path.exists() else "-- Personal keybindings\n"
    menu_original = menu_path.read_text(encoding="utf-8") if menu_path.exists() else "{}\n"
    if action == "install":
        binding_new = install_binding(binding_original, force)
        menu_new = install_menu(menu_original)
    else:
        binding_new = remove_marked(binding_original, BINDING_START, BINDING_END)
        menu_new = remove_menu(menu_original)
    changed: list[Path] = []
    try:
        if binding_new != binding_original:
            atomic_write(binding_path, binding_new)
            changed.append(binding_path)
        if menu_new != menu_original:
            atomic_write(menu_path, menu_new)
            changed.append(menu_path)
    except Exception:
        if binding_path in changed:
            atomic_write(binding_path, binding_original)
        if menu_path in changed:
            atomic_write(menu_path, menu_original)
        raise
    return changed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("install", "remove"))
    parser.add_argument("--force", action="store_true", help="allow adding the binding when SUPER + I is already mentioned")
    args = parser.parse_args()
    try:
        changed = configure(args.action, args.force)
    except ConfigError as exc:
        parser.error(str(exc))
    for path in changed:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
