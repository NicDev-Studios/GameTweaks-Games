# GameTweaks Games Catalog

The community-maintained game and mod catalog for
[GameTweaks](https://github.com/NicDev-Studios/GameTweaks).

It tells the GameTweaks desktop app which Steam games are supported, which mods
are available for them, and which configuration options can be managed from the
app.

## What the catalog contains

- Supported Steam games and their App IDs
- Compatible BepInEx runtime and architecture information
- Mod names, versions, dependencies, and conflicts
- Config controls such as switches, text fields, number inputs, and selections
- Verified release references and SHA-256 checksums

Mods marked **Official** have been reviewed by GameTweaks maintainers. Community
mods use the same validation and installation protections, but do not carry the
Official badge.

## Add a game or mod

Contributions are welcome. To submit a mod:

1. Publish the finished ZIP in a public GitHub release for the mod.
2. Add its definition under `games/<steam-app-id>/mods/`.
3. Reference it from the game's `game.json`.
4. Open a pull request with the release and compatibility evidence.

The catalog checks definitions, checksums, and archive safety automatically.
Approved packages are copied into a protected catalog release before they
become available in GameTweaks.

Read [Adding a game and mods](docs/adding-a-game.md) for the complete format and
[CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request. JSON Schemas
and neutral examples are available in [`schemas/`](schemas/) and
[`examples/`](examples/).

## Safety

GameTweaks downloads mod packages only from this catalog's reviewed releases.
Packages are checksum-verified and inspected before installation. The catalog
does not provide process execution, arbitrary file access, or anti-cheat bypass
functionality.

## License

See [LICENSE](LICENSE).
