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
- A mod release must identify the real public upstream GitHub repository, tag,
  and ZIP asset. Its SHA-256 must match those exact bytes.
- Official mods require a matching public source repository and tag, an exact
  full commit SHA, and the GitHub Actions workflow that built and attested the
  ZIP. Never invent or weaken source provenance fields.
- Never add arbitrary URLs or non-GitHub release hosts. The protected promotion
  workflow mirrors verified bytes into the official catalog release
  `mod-<mod-id>-v<version>` without executing or rebuilding them.
- Keep `official` false unless a GameTweaks maintainer explicitly reviews and
  approves the mod. Official status grants no additional Agent permissions.
- Preserve strict IDs, localized text, semantic versions, runtime and
  architecture compatibility, dependency ordering, conflicts, and bounded
  configuration contracts.
- Schema changes must remain secure and intentionally compatible with the
  desktop parser. Do not weaken required hashes or validation constraints.
- Run `node scripts/validate.mjs` and the schema checks from the catalog workflow.
