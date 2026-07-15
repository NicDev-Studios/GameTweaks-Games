# GameTweaks Games catalog instructions

This repository is a reviewed data and release catalog. It contains no desktop
application code. A game is supported only when `games/<steam-app-id>/game.json`
and every referenced mod definition pass schema, relationship, and digest
validation.

- Read `README.md`, `docs/adding-a-game.md`, and both JSON Schemas before making
  catalog changes.
- Never invent a game, Steam App ID, mod, BepInEx GUID, version, compatibility,
  dependency, conflict, release tag, asset name, digest, or configuration field.
- Do not add example or placeholder entries below `games/`. Neutral examples
  belong only in `examples/`.
- Keep one game at `games/<decimal-app-id>/game.json` and one definition per mod
  at `games/<app-id>/mods/<mod-id>.json`.
- `game.json` is an index. Its SHA-256 must match the exact committed bytes of
  each referenced mod JSON file.
- A mod release SHA-256 must match the exact ZIP asset published in a release of
  this repository.
- Never add arbitrary download URLs or alternate release hosts. The desktop app
  constructs release URLs from the reviewed tag and asset name.
- Keep `official` false unless a GameTweaks maintainer explicitly reviews and
  approves the mod. Official status grants no additional Agent permissions.
- Preserve strict IDs, localized text, semantic versions, runtime and
  architecture compatibility, dependency ordering, conflicts, and bounded
  configuration contracts.
- Schema changes must remain secure and intentionally compatible with the
  desktop parser. Do not weaken required hashes or validation constraints.
- Run `node scripts/validate.mjs` and the schema checks from the catalog workflow.
