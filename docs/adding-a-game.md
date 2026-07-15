# Adding a Game and Mods

## Layout

Create one directory named after the decimal Steam App ID:

```text
games/123456/
  game.json
  mods/
    example.mod.json
```

`game.json` is only an index. Every mod has a separate definition. The SHA-256
in the index must match the exact bytes of that mod JSON file.

## Game index

```json
{
  "schemaVersion": 1,
  "appId": 123456,
  "name": { "en": "Example Game", "de": "Beispielspiel" },
  "mods": [
    {
      "modId": "example.mod",
      "file": "mods/example.mod.json",
      "sha256": "<64 lowercase hexadecimal characters>"
    }
  ]
}
```

The filename, `appId`, referenced `modId`, and definition `modId` must agree.
Paths and arbitrary download URLs are not accepted.

## Mod definition

Every mod release is a ZIP asset in a release of this catalog repository. The
desktop app constructs the download URL from `tag` and `asset`, verifies the
declared SHA-256, validates the archive, then installs it into the mod's own
directory.

Set `official` only after GameTweaks maintainer review. The badge does not grant
the mod additional Agent permissions.

`integration` is either:

- `configFile`: GameTweaks edits the declared BepInEx config while the game is closed.
- `agent`: the shared GameTweaks Agent is installed automatically and the mod can register live values through the SDK.

Dependencies are installed in the same transaction. Conflicts block the
transaction. Removing a dependency is blocked while another installed mod
still needs it.

## Configuration controls

Each field has a stable `id`, BepInEx `section` and `key`, localized label and
an `applyMode` of `live`, `restartRequired`, or `nextLaunch`.

Supported controls:

- `boolean` with `switch` or `checkbox` display
- `string` with a required maximum length
- `integer` and `decimal` with minimum, maximum and step
- `singleSelect` with `dropdown` or `radio` display
- `multiSelect` rendered as a checkbox group

The Agent may add validated fields at runtime. If it reuses a catalog field ID
with a different contract, GameTweaks blocks that field.

## Agent SDK

Reference `GameTweaks.Agent.Abstractions` from the `agent/` source project.
Register the mod once, then register its existing BepInEx config entries. The
Agent only supports configuration and status messages. It cannot start
processes, execute commands, access arbitrary paths, or bypass anti-cheat.

