# Contributing

Keep GlyphTap Omarchy-first, keyboard-first, dependency-light, and private by
default. Do not write to `/usr/share/omarchy`, add telemetry, send local state
to a server, or pass SVG bodies through shell command strings.

Before opening a pull request, run:

```bash
./scripts/test.sh
omarchy plugin validate .
```

For UI changes, install a development checkout, summon the overlay, test the
empty, loading, results, preview, format, favorite, copy, persistent-copy, and
offline states, and inspect the shell log for QML warnings.
