## Catalog change

<!-- What game or mod is added, updated, or corrected, and why? -->

## Identifiers

- Steam App ID:
- Mod ID(s):
- BepInEx GUID(s):

## Release evidence

<!-- List the exact upstream GitHub repository, release tag, ZIP asset name, and how compatibility was verified. -->

## Digests

<!-- List the command used and the resulting SHA-256 for every changed mod JSON and release ZIP. -->

## Automated assistance

<!-- List tools that generated or substantially transformed catalog data or text, and explain how every value was independently verified. Write "None" when not applicable. -->

## Checklist

- [ ] Every value is sourced and verifiable; no game, mod, version, compatibility, or release data was invented.
- [ ] I understand and manually verified every submitted value, including tool-assisted output.
- [ ] Directory, App ID, filename, mod ID, and BepInEx GUID values are internally consistent.
- [ ] Every `game.json` digest matches the exact committed mod JSON bytes.
- [ ] Every release digest matches the exact ZIP asset in the stated upstream GitHub release.
- [ ] Every upstream repository, tag, and asset identifies the mod author's real public release.
- [ ] Dependencies exist, minimum versions are valid, and conflicts are complete.
- [ ] Config defaults, options, bounds, steps, and apply modes match the plugin behavior.
- [ ] I ran `node scripts/validate.mjs`, `python scripts/verify_release_assets.py`, and the JSON Schema checks.
- [ ] `official` remains false, or the required GameTweaks maintainer review is requested.

## Maintainer promotion (when a mod definition changed)

- [ ] The protected **Promote mod assets** workflow succeeded for this pull request; no release asset was uploaded or replaced manually.

## Attention check

<!-- Leave the following box unchecked. Selecting every box without reading flags the pull request for manual verification. -->

- [ ] I selected every checkbox without reading it.
