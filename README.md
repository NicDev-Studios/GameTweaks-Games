# GameTweaks Games Catalog

This directory is the source scaffold for the separate
`NicDev-Studios/GameTweaks-Games` repository. The desktop app only considers a
game supported when `games/<steam-app-id>/game.json` exists and passes all
integrity checks.

No real games or mods are included in the initial catalog.

Contributors publish finished ZIPs in their own public GitHub releases. CI
verifies the exact assets, and a protected maintainer workflow mirrors the
approved bytes into deterministic releases of this repository. The desktop app
continues to trust and download only those mirrored catalog releases.

Set the repository variable `OFFICIAL_REVIEWERS` to a comma-separated list of
maintainer GitHub usernames and require the catalog workflow plus CODEOWNERS
approval in branch protection. A pull request that newly sets `official: true`
then fails until one of those maintainers approves it.

Create a protected GitHub environment named `catalog-publishing`, restrict it to
the `main` branch, and configure required maintainer reviewers. The **Promote mod
assets** workflow uses this environment and requires only `contents: write` plus
read access to pull requests. Enable immutable releases in the repository
settings so GitHub also prevents later modification of published catalog assets.

See [Adding a game](docs/adding-a-game.md) and the JSON Schemas in `schemas/`.
Contributors must also follow [CONTRIBUTING.md](CONTRIBUTING.md), including its
verification and automated-assistance disclosure requirements.
