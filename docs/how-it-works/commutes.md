---
icon: lucide/briefcase
---

# Commutes

Commute places live in `src/casita/places.py` and are routed by
`walk.populate_for_places` in `src/casita/walk.py`.

Casita's curated anchors (beaches, trails, bakeries) are lifestyle amenities —
"how close is the nearest good bakery." Commutes are different: they're
obligations you have regardless of whether a listing is convenient, so they
get their own category end to end — config, routing, score, LLM prompt, and
render surfaces — rather than merging into the anchor logic.

Declare places you travel to regularly in `places.yaml`, one entry per
destination:

```yaml
commutes:
  - name: "Work — Financial District"
    short: Work
    lat: 37.7897
    lng: -122.3972
    importance: 1          # 1 = near-daily, 2 = weekly-ish, 3 = occasional
    mode: transit           # walk | drive | transit
    cadence: "weekdays"     # free text, shown as context
    target_minutes: 35      # what counts as "good" — drives color + score
```

`places.example.yaml` is the committed template with three public San
Francisco landmarks, so the feature is visible in `uv run casita demo` with
no real address ever entering the tree. `places.yaml` itself is gitignored —
see the Public-Repo Contract in `CLAUDE.md`.

The feature is opt-in and degrades to nothing: with no `places.yaml`,
`load_places()` returns `[]` and every downstream consumer — score, prompt,
render — is byte-identical to the commute-less baseline.

## How it scores

Each place is scored against its own `target_minutes`, not a global
constant — a 40-minute transit commute is fine, a 40-minute walk to a bakery
is not. The bonus is weighted by `importance`: near-daily places move the
score roughly 3x more than occasional ones (`rank._commute_bonus`).

The Gemini ranking prompt gets the same signal, in a `COMMUTES:` clause
appended to each listing's brief. An importance-1 (near-daily) place more
than 2x over target can push a listing to `severity="filtered"` — the only
category besides the dog-policy gate allowed to do that.

## Routing

`populate_for_places` groups places by `mode` and issues one
`computeRouteMatrix` call per mode per origin chunk, since a single request
carries one `travelMode`. TRANSIT requests attach a canonical departure time
(next weekday 08:30 America/Los_Angeles) — required by the API, and
deliberately excluded from the route-cache key, so results read as "typical
weekday morning" rather than being invalidated by the calendar.

!!! warning "Google Maps cost"

    Commute routing shares the same paid Routes API and cache as the curated
    anchors — see [Routing](routing.md). TRANSIT stays on the Essentials
    billing SKU as long as no `routingPreference` is set; Casita never sets
    one on TRANSIT calls. Set `CASITA_ROUTES_OFFLINE=1` to force haversine
    fallback (drive time × 1.8 for transit) even with a Maps key set.

## Render surfaces

The detail page shows every declared place, sorted by importance, above the
trail/beach/bakery rows (`listing_page._render_kv`). The card shows at most
one chip — the worst importance-1 place, since that's the one that would
actually make the listing unworkable (`html._worst_commute`).

## Ways This Could Go Further

Places currently require hand-entered lat/lng — there's no geocoder in the
codebase. A `casita places geocode` verb could resolve addresses once and
cache the result. Transit is drive/walk's newest sibling; if it proves too
noisy in practice, the mode could ship behind a flag instead of always-on.
