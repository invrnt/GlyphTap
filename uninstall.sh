#!/usr/bin/env bash
set -euo pipefail

glyphtap_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
glyphtap_purge=false
if [[ ${1:-} == --purge ]]; then
  glyphtap_purge=true
  shift
fi
if (( $# > 0 )); then
  echo "Usage: ./uninstall.sh [--purge]" >&2
  exit 2
fi

python3 "$glyphtap_root/scripts/configure.py" remove

glyphtap_bin="$HOME/.local/bin/glyphtap"
if [[ -f $glyphtap_bin ]] && cmp -s "$glyphtap_root/scripts/glyphtap" "$glyphtap_bin"; then
  rm -f -- "$glyphtap_bin"
fi

hyprctl reload >/dev/null 2>&1 || true
omarchy-shell shell rescanPlugins >/dev/null 2>&1 || true
omarchy plugin disable io.github.juancamilogra.glyphtap >/dev/null 2>&1 || true

if [[ $glyphtap_purge == true ]]; then
  glyphtap_state="${XDG_STATE_HOME:-$HOME/.local/state}/glyphtap"
  [[ -n $glyphtap_state && $glyphtap_state != / && $glyphtap_state != "$HOME" ]] || {
    echo "Refusing unsafe purge target: $glyphtap_state" >&2
    exit 1
  }
  rm -rf -- "$glyphtap_state"
  echo "GlyphTap integration, favorites, recents, and cache were removed."
else
  echo "GlyphTap integration was removed. Favorites, recents, and cache were preserved."
fi

echo "Remove the plugin checkout separately with: omarchy plugin remove io.github.juancamilogra.glyphtap"
