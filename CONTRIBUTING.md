# Contributing to the GameTweaks Games catalog

Read `docs/adding-a-game.md` and both JSON Schemas before adding or changing a
game or mod. Every catalog value must come from a real, authoritative source or
from a reproducible inspection of the actual game or plugin.

## Verification requirements

- Never invent or guess Steam App IDs, BepInEx GUIDs, versions, compatibility,
  dependencies, conflicts, configuration fields, releases, or hashes.
- Compute hashes from the exact committed JSON and published ZIP bytes.
- Keep examples outside `games/`; placeholder catalog entries are forbidden.
- Keep `official` false unless a GameTweaks maintainer explicitly reviews it.
- Publish the final ZIP in a public release of the mod's real GitHub repository.
- Run `node scripts/validate.mjs`, `python scripts/verify_release_assets.py`, and
  the JSON Schema checks before submitting.
- List the exact checks and hash commands you actually ran in the pull request.

Maintainers must run the protected **Promote mod assets** workflow for the pull
request and confirm that it succeeds before merging. The workflow copies the
verified upstream bytes into an immutable official catalog release; do not
upload, replace, or rebuild mod ZIPs manually.

## Automated assistance

Automated tools may assist a contribution, but they are not an authoritative
source for catalog facts. Disclose material automated assistance in the pull
request and independently verify every generated or transformed value against
the real upstream project, release asset, or game installation.

Fabricated data, generic filler, guessed compatibility, false validation claims,
and blindly selected checklists are grounds for closing a contribution. Reviews
must focus on objective evidence and must not infer AI use from writing style.
