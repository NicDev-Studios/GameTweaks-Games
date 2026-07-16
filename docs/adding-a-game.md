# Adding a Game and Mods

## Layout

Create one directory named after the decimal Steam App ID:

```text
games/123456/
  game.json
  mods/                    # only when the game has catalog mods
    example.mod.json
```

`game.json` is only an index. Every mod has a separate definition. The SHA-256
in the index must match the exact bytes of that mod JSON file.

A game can be added before any mods exist. In that case, set `mods` to an empty
array and do not create an empty `mods/` directory.

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

For a game without catalog mods, use:

```json
{
  "schemaVersion": 1,
  "appId": 123456,
  "name": { "en": "Example Game" },
  "mods": []
}
```

The filename, `appId`, referenced `modId`, and definition `modId` must agree.
Paths and arbitrary download URLs are not accepted.

## Mod definition

Publish the finished mod ZIP in a public GitHub release owned by the mod
project. The `release` object identifies that upstream repository, tag, asset,
and the SHA-256 of the exact ZIP bytes:

```json
"release": {
  "repository": "author/mod-repository",
  "tag": "v1.0.0",
  "asset": "author.mod.zip",
  "sha256": "<64 lowercase hexadecimal characters>"
}
```

Pull-request CI downloads this exact upstream asset without repository secrets,
checks its digest and archive structure, and rejects unsafe or mismatched
packages. After review, a maintainer runs the protected **Promote mod assets**
workflow for the pull-request number. It mirrors the already verified bytes into
the official catalog release `mod-<mod-id>-v<version>`; it never builds or
executes contributor code. Existing catalog releases are never modified.

The desktop app still downloads only from this catalog repository. It verifies
the declared SHA-256 again, validates the archive again, then installs it into
the mod's own directory. Merge the pull request only after promotion succeeds.

Set `official` only after GameTweaks maintainer review. The badge does not grant
the mod additional Agent permissions.

### Official source and build provenance

An Official mod must be open source and built in its public release repository.
Add the exact tag, commit, and GitHub Actions workflow that produced the ZIP:

```json
"source": {
  "repository": "author/mod-repository",
  "tag": "v1.0.0",
  "commit": "0123456789abcdef0123456789abcdef01234567",
  "workflow": ".github/workflows/release.yml"
}
```

The source repository and tag must exactly match `release.repository` and
`release.tag`. The tag must still resolve to the declared commit. The release
workflow must build the ZIP on a GitHub-hosted runner and create GitHub build
provenance for that exact ZIP. The verifier binds the attestation to the
repository, workflow path, tag ref, commit, and ZIP digest; attestations from
self-hosted runners are rejected.

The release workflow needs these permissions and an attestation step after the
ZIP is built:

```yaml
permissions:
  contents: write
  id-token: write
  attestations: write

steps:
  # Check out the tag, restore locked dependencies, build, and create dist/mod.zip.
  - name: Attest release ZIP
    uses: actions/attest@v4
    with:
      subject-path: dist/mod.zip

  - name: Publish immutable release
    env:
      GH_TOKEN: ${{ github.token }}
    run: gh release create "$GITHUB_REF_NAME" dist/mod.zip --verify-tag --generate-notes
```

Pin third-party actions to full commit SHAs, lock build dependencies, and make
ZIP creation deterministic where the toolchain permits it. An attestation
provides verifiable build provenance; it does not by itself prove that the
source is safe or that two independent builds are byte-for-byte reproducible.

For Community mods, `source` is optional. If supplied, it is validated and its
attestation is enforced in exactly the same way. Official submissions require a
GameTweaks maintainer to review the source changes and release workflow before
approving the current catalog pull-request commit.

`integration` is either:

- `configFile`: GameTweaks edits the declared BepInEx config while the game is closed.
- `agent`: the shared GameTweaks Agent is installed automatically and the mod can register live values through the SDK.

An Agent integration must set `compatibility.minimumAgentVersion` to the oldest
Agent version tested with that mod release. A config-file integration must not
set it.

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

Install the published
[`GameTweaks.Agent.Abstractions`](https://www.nuget.org/packages/GameTweaks.Agent.Abstractions)
package as a private compile-only dependency:

```xml
<PackageReference Include="GameTweaks.Agent.Abstractions" Version="0.1.0">
  <IncludeAssets>compile</IncludeAssets>
  <PrivateAssets>all</PrivateAssets>
</PackageReference>
```

Declare a hard BepInEx dependency with the same minimum version:

```csharp
[BepInDependency("dev.gametweaks.agent", "0.1.0")]
```

Follow the
[complete Agent SDK guide](https://github.com/NicDev-Studios/GameTweaks/blob/main/agent/SDK.md)
for lifecycle-safe registration, bindings, and a buildable plugin example.
`modId` must match `ModRegistration.ModId`, `guid` must match the
`BepInPlugin` GUID, and registered fields must match catalog fields with the
same ID exactly.

Do not put `GameTweaks.Agent.Abstractions.dll` or any other
`GameTweaks.Agent.*.dll` in the mod ZIP. The shared runtime is installed and
owned by GameTweaks, and archives containing those assemblies are rejected.
The Agent only supports configuration and status messages. It cannot start
processes, execute commands, access arbitrary paths, or bypass anti-cheat.

## Contributor workflow

1. Publish the final ZIP in your mod repository's public GitHub release. For an
   Official mod, build and attest it through the declared GitHub Actions workflow.
2. Add or update the mod definition and compute the ZIP SHA-256. Official mods
   must also declare `source` with the exact tag, commit, and workflow.
3. Update `game.json` with the SHA-256 of the exact mod JSON bytes.
4. Run `node scripts/validate.mjs` and
   `python scripts/verify_release_assets.py`.
5. Open a pull request and wait for catalog validation.
6. For Official mods, a maintainer reviews the source diff and build workflow,
   then approves the current pull-request commit.
7. A maintainer runs **Promote mod assets** and merges only after the promotion
   succeeds.
