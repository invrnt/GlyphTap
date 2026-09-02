#!/usr/bin/env bash
set -euo pipefail

glyphtap_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
glyphtap_force=false

if [[ ${1:-} == --force ]]; then
  glyphtap_force=true
  shift
fi
if (( $# > 0 )); then
  echo "Usage: ./install.sh [--force]" >&2
  exit 2
fi

for glyphtap_command in omarchy omarchy-shell python3 wl-copy; do
  command -v "$glyphtap_command" >/dev/null 2>&1 || {
    echo "GlyphTap requires '$glyphtap_command'. On Omarchy, install missing runtime packages with: omarchy pkg add python wl-clipboard" >&2
    exit 1
  }
done

omarchy plugin validate "$glyphtap_root"

glyphtap_bin_dir="$HOME/.local/bin"
glyphtap_bin="$glyphtap_bin_dir/glyphtap"
install -d -m 755 "$glyphtap_bin_dir"
if [[ -L $glyphtap_bin || (-e $glyphtap_bin && ! -f $glyphtap_bin) ]]; then
  echo "Refusing to replace non-regular path: $glyphtap_bin" >&2
  exit 1
fi
if [[ -f $glyphtap_bin ]] && ! cmp -s "$glyphtap_root/scripts/glyphtap" "$glyphtap_bin"; then
  echo "Refusing to overwrite an unrelated command: $glyphtap_bin" >&2
  exit 1
fi

glyphtap_stage="$(mktemp "$glyphtap_bin_dir/.glyphtap.XXXXXX")"
trap 'rm -f -- "$glyphtap_stage"' EXIT
install -m 755 "$glyphtap_root/scripts/glyphtap" "$glyphtap_stage"
glyphtap_created_bin=false
if [[ ! -e $glyphtap_bin ]]; then
  mv -- "$glyphtap_stage" "$glyphtap_bin"
  glyphtap_created_bin=true
else
  rm -f -- "$glyphtap_stage"
fi

glyphtap_config_args=(install)
[[ $glyphtap_force == true ]] && glyphtap_config_args+=(--force)
if ! python3 "$glyphtap_root/scripts/configure.py" "${glyphtap_config_args[@]}"; then
  [[ $glyphtap_created_bin == true ]] && rm -f -- "$glyphtap_bin"
  exit 1
fi
trap - EXIT

hyprctl reload >/dev/null || echo "GlyphTap was installed, but Hyprland could not reload automatically." >&2
omarchy-shell shell rescanPlugins >/dev/null
omarchy plugin enable io.github.juancamilogra.glyphtap >/dev/null

echo "GlyphTap integration is ready: press Super + I or open GlyphTap from Super + Space."
