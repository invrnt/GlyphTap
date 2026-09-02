#!/usr/bin/env bash
set -euo pipefail

glyphtap_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$glyphtap_root"

PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY'
from pathlib import Path

for root in (Path("."), Path("scripts"), Path("tests")):
    for source in root.glob("*.py"):
        compile(source.read_text(encoding="utf-8"), str(source), "exec")
PY
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
bash -n install.sh uninstall.sh scripts/glyphtap scripts/test.sh
python3 -m json.tool manifest.json >/dev/null

python3 - <<'PY'
import json
import re
from pathlib import Path

manifest = json.loads(Path("manifest.json").read_text(encoding="utf-8"))
assert re.fullmatch(r"\d+\.\d+\.\d+", manifest["version"])
assert manifest["id"] == "io.github.juancamilogra.glyphtap"
assert manifest["kinds"] == ["overlay"]
assert Path(manifest["entryPoints"]["overlay"]).is_file()
assert Path("preview.png").is_file()
assert Path("LICENSE").is_file()
assert Path("README.md").is_file()
PY

if command -v omarchy >/dev/null 2>&1; then
  omarchy plugin validate .
fi

if find . -path ./.git -prune -o -type l -print -quit | grep -q .; then
  echo "Symlinks must not ship in GlyphTap." >&2
  exit 1
fi

echo "All GlyphTap checks passed."
