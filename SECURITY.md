# Security policy

## Data and network boundaries

GlyphTap sends only the text typed into its search field to
`https://api.iconify.design`. It has no account, analytics, telemetry, update
service, or project server. Favorites, recents, preferred output format, query
results, and recently fetched icon bodies stay under
`${XDG_STATE_HOME:-~/.local/state}/glyphtap/`.

The cache is capped at 24 MiB. State writes are atomic and private to the user.
SVG markup is passed to `wl-copy` on standard input, never through a shell or
command-line argument. Network responses and identifiers have explicit size
and syntax limits.

The optional installer edits only the current user's
`~/.config/hypr/bindings.lua`,
`~/.config/omarchy/extensions/omarchy-menu.jsonc`, and
`~/.local/bin/glyphtap`. Managed markers make these changes idempotent and
reversible. It never writes to `/usr/share/omarchy` and refuses a conflicting
`Super + I` binding unless `--force` is explicit.

## Reporting a vulnerability

Please use GitHub's private vulnerability reporting for this repository. Do
not include credentials or unrelated personal data in a public issue.
