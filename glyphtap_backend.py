#!/usr/bin/env python3
"""Small, dependency-free Iconify client used by the GlyphTap QML overlay."""

from __future__ import annotations

import argparse
import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import html
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, build_opener, HTTPRedirectHandler


API_ORIGIN = "https://api.iconify.design"
USER_AGENT = "GlyphTap/1.0 (+https://github.com/JuanCamiloGrA/GlyphTap)"
MAX_RESPONSE_BYTES = 8 * 1024 * 1024
MAX_CACHE_BYTES = 24 * 1024 * 1024
MAX_ICONS = 96
MAX_RECENTS = 24
MAX_FAVORITES = 200
QUERY_TTL_SECONDS = 7 * 24 * 60 * 60
COLLECTION_TTL_SECONDS = 14 * 24 * 60 * 60
ICON_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}:[a-z0-9][a-z0-9-]{0,127}$")
COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")


class GlyphTapError(RuntimeError):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        raise GlyphTapError("Iconify returned an unexpected redirect")


def state_root() -> Path:
    base = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state"))
    return base / "glyphtap"


def ensure_private_dir(path: Path) -> None:
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.is_symlink() or not path.is_dir():
        raise GlyphTapError(f"Unsafe state directory: {path}")
    try:
        path.chmod(0o700)
    except OSError:
        pass


def atomic_json(path: Path, value: Any) -> None:
    ensure_private_dir(path.parent)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, separators=(",", ":"))
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def read_json(path: Path, fallback: Any, max_bytes: int = MAX_RESPONSE_BYTES) -> Any:
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > max_bytes:
            return fallback
        with path.open("r", encoding="utf-8") as stream:
            return json.load(stream)
    except (OSError, ValueError, TypeError):
        return fallback


def cache_path(group: str, key: str) -> Path:
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return state_root() / "cache" / group / f"{digest}.json"


def fresh(path: Path, ttl: int) -> bool:
    try:
        return path.is_file() and not path.is_symlink() and time.time() - path.stat().st_mtime <= ttl
    except OSError:
        return False


def fetch_json(endpoint: str, params: dict[str, str] | None = None) -> dict[str, Any]:
    if not endpoint.startswith("/") or ".." in endpoint:
        raise GlyphTapError("Invalid Iconify endpoint")
    url = API_ORIGIN + endpoint
    if params:
        url += "?" + urlencode(params)
    request = Request(url, headers={"Accept": "application/json", "User-Agent": USER_AGENT})
    try:
        with build_opener(NoRedirect).open(request, timeout=7) as response:
            length = response.headers.get("Content-Length")
            if length and int(length) > MAX_RESPONSE_BYTES:
                raise GlyphTapError("Iconify response was too large")
            raw = response.read(MAX_RESPONSE_BYTES + 1)
    except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
        raise GlyphTapError(f"Iconify is unavailable: {exc}") from exc
    if len(raw) > MAX_RESPONSE_BYTES:
        raise GlyphTapError("Iconify response was too large")
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GlyphTapError("Iconify returned invalid JSON") from exc
    if not isinstance(value, dict):
        raise GlyphTapError("Iconify returned an unexpected response")
    return value


def default_library() -> dict[str, Any]:
    return {"version": 1, "favorites": [], "recents": [], "preferred_format": "svg"}


def load_library() -> dict[str, Any]:
    value = read_json(state_root() / "library.json", default_library(), 256 * 1024)
    if not isinstance(value, dict):
        value = default_library()
    favorites = [item for item in value.get("favorites", []) if isinstance(item, str) and ICON_ID.fullmatch(item)]
    recents = [item for item in value.get("recents", []) if isinstance(item, str) and ICON_ID.fullmatch(item)]
    preferred = value.get("preferred_format", "svg")
    if preferred not in OUTPUT_FORMATS:
        preferred = "svg"
    return {
        "version": 1,
        "favorites": favorites[:MAX_FAVORITES],
        "recents": recents[:MAX_RECENTS],
        "preferred_format": preferred,
    }


def save_library(value: dict[str, Any]) -> None:
    atomic_json(state_root() / "library.json", value)


def valid_icon_id(value: str) -> str:
    value = value.strip().lower()
    if not ICON_ID.fullmatch(value):
        raise GlyphTapError("Invalid Iconify icon name")
    return value


def icon_cache(icon_id: str) -> Path:
    return cache_path("icons", icon_id)


def query_cache(query: str) -> Path:
    return cache_path("queries", query.casefold())


def resolve_icon(icon_set: dict[str, Any], name: str, seen: set[str] | None = None) -> dict[str, Any] | None:
    icons = icon_set.get("icons", {})
    aliases = icon_set.get("aliases", {})
    if isinstance(icons, dict) and isinstance(icons.get(name), dict):
        row = dict(icons[name])
        row["width"] = row.get("width", icon_set.get("width", 16))
        row["height"] = row.get("height", icon_set.get("height", 16))
        return row
    if not isinstance(aliases, dict) or not isinstance(aliases.get(name), dict):
        return None
    seen = set() if seen is None else seen
    if name in seen or len(seen) > 8:
        return None
    seen.add(name)
    alias = aliases[name]
    parent = alias.get("parent")
    if not isinstance(parent, str):
        return None
    row = resolve_icon(icon_set, parent, seen)
    if not row:
        return None
    body = str(row.get("body", ""))
    width = int(alias.get("width", row.get("width", 16)))
    height = int(alias.get("height", row.get("height", 16)))
    if alias.get("hFlip"):
        body = f'<g transform="translate({width} 0) scale(-1 1)">{body}</g>'
    if alias.get("vFlip"):
        body = f'<g transform="translate(0 {height}) scale(1 -1)">{body}</g>'
    rotate = int(alias.get("rotate", 0)) % 4
    if rotate == 1:
        body = f'<g transform="translate({height} 0) rotate(90)">{body}</g>'
        width, height = height, width
    elif rotate == 2:
        body = f'<g transform="translate({width} {height}) rotate(180)">{body}</g>'
    elif rotate == 3:
        body = f'<g transform="translate(0 {width}) rotate(270)">{body}</g>'
        width, height = height, width
    row.update({"body": body, "width": width, "height": height})
    return row


def fetch_icon_group(prefix: str, names: list[str]) -> dict[str, dict[str, Any]]:
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", prefix):
        return {}
    value = fetch_json(f"/{prefix}.json", {"icons": ",".join(names)})
    resolved: dict[str, dict[str, Any]] = {}
    for name in names:
        row = resolve_icon(value, name)
        if not row or not isinstance(row.get("body"), str) or not safe_svg_body(row["body"]):
            continue
        icon_id = f"{prefix}:{name}"
        cached = {
            "id": icon_id,
            "body": row["body"],
            "width": max(1, min(int(row.get("width", 16)), 1024)),
            "height": max(1, min(int(row.get("height", 16)), 1024)),
        }
        atomic_json(icon_cache(icon_id), cached)
        resolved[icon_id] = cached
    return resolved


def safe_svg_body(body: str) -> bool:
    if not body or len(body.encode("utf-8")) > 256 * 1024:
        return False
    folded = body.casefold()
    if any(token in folded for token in ("<script", "<foreignobject", "javascript:", "data:text/html")):
        return False
    if re.search(r"\son[a-z0-9_-]+\s*=", folded):
        return False
    if re.search(r"(?:href|xlink:href)\s*=\s*[\"']\s*(?:https?:|//)", folded):
        return False
    return True


def load_icons(icon_ids: list[str], allow_network: bool = True) -> dict[str, dict[str, Any]]:
    loaded: dict[str, dict[str, Any]] = {}
    missing: dict[str, list[str]] = {}
    for raw in icon_ids:
        try:
            icon_id = valid_icon_id(raw)
        except GlyphTapError:
            continue
        cached = read_json(icon_cache(icon_id), None, 512 * 1024)
        if isinstance(cached, dict) and isinstance(cached.get("body"), str):
            loaded[icon_id] = cached
        elif allow_network:
            prefix, name = icon_id.split(":", 1)
            missing.setdefault(prefix, []).append(name)
    batches = [
        (prefix, names[offset : offset + 40])
        for prefix, names in missing.items()
        for offset in range(0, len(names), 40)
    ]
    if batches:
        with ThreadPoolExecutor(max_workers=min(8, len(batches)), thread_name_prefix="glyphtap") as pool:
            futures = [pool.submit(fetch_icon_group, prefix, names) for prefix, names in batches]
            first_error: Exception | None = None
            for future in as_completed(futures):
                try:
                    loaded.update(future.result())
                except Exception as exc:
                    first_error = first_error or exc
            if first_error and not loaded:
                if isinstance(first_error, GlyphTapError):
                    raise first_error
                raise GlyphTapError("Could not fetch icon data") from first_error
    return loaded


def collection_metadata(prefixes: list[str], allow_network: bool = True) -> dict[str, Any]:
    path = state_root() / "cache" / "collections.json"
    value = read_json(path, {}, 4 * 1024 * 1024)
    if not isinstance(value, dict):
        value = {}
    missing = [prefix for prefix in prefixes if prefix not in value]
    if allow_network and (missing or not fresh(path, COLLECTION_TTL_SECONDS)):
        try:
            remote = fetch_json("/collections", {"prefixes": ",".join(sorted(set(prefixes)))})
            value.update(remote)
            atomic_json(path, value)
        except GlyphTapError:
            pass
    return value


def svg_markup(row: dict[str, Any], color: str | None = None) -> str:
    width = int(row.get("width", 16))
    height = int(row.get("height", 16))
    body = str(row.get("body", ""))
    if color:
        body = body.replace("currentColor", color)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">{body}</svg>'
    )


def display_row(icon_id: str, row: dict[str, Any], collections: dict[str, Any], library: dict[str, Any], color: str) -> dict[str, Any]:
    prefix, name = icon_id.split(":", 1)
    collection = collections.get(prefix, {}) if isinstance(collections, dict) else {}
    if not isinstance(collection, dict):
        collection = {}
    license_data = collection.get("license", {})
    if not isinstance(license_data, dict):
        license_data = {}
    svg = svg_markup(row, color)
    encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return {
        "id": icon_id,
        "prefix": prefix,
        "name": name,
        "collection": str(collection.get("name") or prefix),
        "license": str(license_data.get("spdx") or license_data.get("title") or "See collection"),
        "width": int(row.get("width", 16)),
        "height": int(row.get("height", 16)),
        "favorite": icon_id in library["favorites"],
        "source": "data:image/svg+xml;base64," + encoded,
    }


def local_matches(query: str, limit: int) -> list[str]:
    terms = [term for term in re.split(r"[^a-z0-9]+", query.casefold()) if term]
    matches: list[tuple[int, str]] = []
    icon_dir = state_root() / "cache" / "icons"
    if not icon_dir.is_dir() or icon_dir.is_symlink():
        return []
    for path in icon_dir.glob("*.json"):
        value = read_json(path, None, 512 * 1024)
        icon_id = value.get("id", "") if isinstance(value, dict) else ""
        if not isinstance(icon_id, str) or not ICON_ID.fullmatch(icon_id):
            continue
        folded = icon_id.casefold()
        if all(term in folded for term in terms):
            score = sum(folded.find(term) for term in terms)
            matches.append((score, icon_id))
    matches.sort(key=lambda item: (item[0], item[1]))
    return [item[1] for item in matches[:limit]]


def ranked(ids: list[str], library: dict[str, Any]) -> list[str]:
    favorites = {value: index for index, value in enumerate(library["favorites"])}
    recents = {value: index for index, value in enumerate(library["recents"])}
    original = {value: index for index, value in enumerate(ids)}
    unique = list(dict.fromkeys(ids))
    return sorted(
        unique,
        key=lambda value: (
            0 if value in favorites else 1,
            favorites.get(value, 9999),
            0 if value in recents else 1,
            recents.get(value, 9999),
            original.get(value, 9999),
        ),
    )


def command_search(args: argparse.Namespace) -> dict[str, Any]:
    query = " ".join(args.query.strip().split())[:100]
    color = args.color if COLOR.fullmatch(args.color) else "#f5f5f5"
    limit = max(1, min(args.limit, MAX_ICONS))
    library = load_library()
    online = True
    message = ""
    if query:
        path = query_cache(query)
        cached = read_json(path, {}, 512 * 1024)
        ids = cached.get("icons", []) if isinstance(cached, dict) else []
        if not fresh(path, QUERY_TTL_SECONDS):
            try:
                response = fetch_json("/search", {"query": query, "limit": str(limit)})
                ids = response.get("icons", [])
                if not isinstance(ids, list):
                    ids = []
                ids = [item for item in ids if isinstance(item, str) and ICON_ID.fullmatch(item)][:limit]
                atomic_json(path, {"query": query, "icons": ids, "saved_at": int(time.time())})
            except GlyphTapError as exc:
                online = False
                message = str(exc)
                if not ids:
                    ids = local_matches(query, limit)
    else:
        ids = list(dict.fromkeys(library["recents"] + library["favorites"]))[:limit]
    ids = ranked([item for item in ids if isinstance(item, str) and ICON_ID.fullmatch(item)], library)[:limit]
    try:
        icons = load_icons(ids, allow_network=online)
    except GlyphTapError as exc:
        online = False
        message = str(exc)
        icons = load_icons(ids, allow_network=False)
    visible_ids = [icon_id for icon_id in ids if icon_id in icons]
    prefixes = list(dict.fromkeys(icon_id.split(":", 1)[0] for icon_id in visible_ids))
    collections = collection_metadata(prefixes, allow_network=online)
    rows = [display_row(icon_id, icons[icon_id], collections, library, color) for icon_id in visible_ids]
    prune_cache()
    return {
        "ok": True,
        "query": query,
        "online": online,
        "message": message,
        "preferred_format": library["preferred_format"],
        "icons": rows,
    }


def jsx_markup(svg: str) -> str:
    replacements = {
        "class=": "className=",
        "stroke-linecap=": "strokeLinecap=",
        "stroke-linejoin=": "strokeLinejoin=",
        "stroke-width=": "strokeWidth=",
        "fill-rule=": "fillRule=",
        "clip-rule=": "clipRule=",
        "color-interpolation-filters=": "colorInterpolationFilters=",
    }
    for before, after in replacements.items():
        svg = svg.replace(before, after)
    return svg


def css_data_uri(svg: str) -> str:
    compact = re.sub(r">\s+<", "><", svg).replace("#", "%23")
    return "data:image/svg+xml," + quote(compact, safe="/:;=,+-_.!~*'()\"")


OUTPUT_FORMATS = {
    "svg": lambda icon_id, svg: svg,
    "name": lambda icon_id, svg: icon_id,
    "jsx": lambda icon_id, svg: jsx_markup(svg),
    "react": lambda icon_id, svg: f'import {{ Icon }} from "@iconify/react";\n\n<Icon icon="{icon_id}" />',
    "vue": lambda icon_id, svg: f'<script setup>\nimport {{ Icon }} from "@iconify/vue";\n</script>\n\n<Icon icon="{icon_id}" />',
    "html": lambda icon_id, svg: svg,
    "css": lambda icon_id, svg: f'.icon {{\n  background-color: currentColor;\n  mask: url("{css_data_uri(svg)}") center / contain no-repeat;\n}}',
    "data-uri": lambda icon_id, svg: css_data_uri(svg),
}


def one_icon(icon_id: str) -> dict[str, Any]:
    icon_id = valid_icon_id(icon_id)
    try:
        icons = load_icons([icon_id], allow_network=True)
    except GlyphTapError:
        icons = load_icons([icon_id], allow_network=False)
    if icon_id not in icons:
        raise GlyphTapError("That icon is not available online or in the local cache")
    return icons[icon_id]


def remember(icon_id: str, output_format: str | None = None) -> dict[str, Any]:
    library = load_library()
    library["recents"] = [icon_id] + [item for item in library["recents"] if item != icon_id]
    library["recents"] = library["recents"][:MAX_RECENTS]
    if output_format in OUTPUT_FORMATS:
        library["preferred_format"] = output_format
    save_library(library)
    return library


def command_copy(args: argparse.Namespace) -> dict[str, Any]:
    icon_id = valid_icon_id(args.icon)
    if args.format not in OUTPUT_FORMATS:
        raise GlyphTapError("Unsupported copy format")
    svg = svg_markup(one_icon(icon_id))
    output = OUTPUT_FORMATS[args.format](icon_id, svg)
    try:
        subprocess.run(
            ["wl-copy", "--type", "image/svg+xml" if args.format == "svg" else "text/plain;charset=utf-8"],
            input=output.encode("utf-8"),
            check=True,
            timeout=4,
        )
    except (FileNotFoundError, subprocess.SubprocessError) as exc:
        raise GlyphTapError("Could not copy: wl-copy is required") from exc
    remember(icon_id, args.format)
    return {"ok": True, "icon": icon_id, "format": args.format, "message": f"Copied {args.format.upper()} · {icon_id}"}


def command_save(args: argparse.Namespace) -> dict[str, Any]:
    icon_id = valid_icon_id(args.icon)
    svg = svg_markup(one_icon(icon_id))
    target_dir = Path(args.directory).expanduser() if args.directory else Path.home() / "Downloads"
    target_dir.mkdir(parents=True, exist_ok=True)
    if target_dir.is_symlink() or not target_dir.is_dir():
        raise GlyphTapError("Unsafe save directory")
    name = icon_id.replace(":", "-") + ".svg"
    target = target_dir / name
    target.write_text(svg + "\n", encoding="utf-8")
    remember(icon_id)
    return {"ok": True, "icon": icon_id, "path": str(target), "message": f"Saved {name}"}


def command_favorite(args: argparse.Namespace) -> dict[str, Any]:
    icon_id = valid_icon_id(args.icon)
    library = load_library()
    if icon_id in library["favorites"]:
        library["favorites"].remove(icon_id)
        favorite = False
    else:
        library["favorites"].insert(0, icon_id)
        library["favorites"] = library["favorites"][:MAX_FAVORITES]
        favorite = True
    save_library(library)
    return {"ok": True, "icon": icon_id, "favorite": favorite, "message": "Added to favorites" if favorite else "Removed from favorites"}


def command_info(args: argparse.Namespace) -> dict[str, Any]:
    library = load_library()
    return {"ok": True, **library}


def prune_cache() -> None:
    cache = state_root() / "cache"
    if not cache.is_dir() or cache.is_symlink():
        return
    files: list[tuple[float, int, Path]] = []
    total = 0
    for path in cache.rglob("*.json"):
        try:
            if path.is_symlink() or not path.is_file():
                continue
            stat = path.stat()
            files.append((stat.st_mtime, stat.st_size, path))
            total += stat.st_size
        except OSError:
            continue
    if total <= MAX_CACHE_BYTES:
        return
    for _, size, path in sorted(files):
        try:
            path.unlink()
            total -= size
        except OSError:
            pass
        if total <= MAX_CACHE_BYTES * 3 // 4:
            break


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="glyphtap-backend")
    commands = root.add_subparsers(dest="command", required=True)
    search = commands.add_parser("search")
    search.add_argument("--query", default="")
    search.add_argument("--color", default="#f5f5f5")
    search.add_argument("--limit", type=int, default=64)
    search.set_defaults(handler=command_search)
    copy = commands.add_parser("copy")
    copy.add_argument("icon")
    copy.add_argument("format", choices=sorted(OUTPUT_FORMATS))
    copy.set_defaults(handler=command_copy)
    save = commands.add_parser("save")
    save.add_argument("icon")
    save.add_argument("--directory", default="")
    save.set_defaults(handler=command_save)
    favorite = commands.add_parser("favorite")
    favorite.add_argument("icon")
    favorite.set_defaults(handler=command_favorite)
    info = commands.add_parser("info")
    info.set_defaults(handler=command_info)
    return root


def main(argv: list[str] | None = None) -> int:
    try:
        args = parser().parse_args(argv)
        result = args.handler(args)
    except GlyphTapError as exc:
        result = {"ok": False, "message": str(exc)}
    except Exception as exc:  # keep the long-running shell insulated from backend faults
        result = {"ok": False, "message": f"GlyphTap backend error: {type(exc).__name__}"}
    json.dump(result, sys.stdout, ensure_ascii=False, separators=(",", ":"))
    sys.stdout.write("\n")
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
