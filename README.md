# GameTweaks Games Catalog

This directory is the source scaffold for the separate
`NicDev-Studios/GameTweaks-Games` repository. The desktop app only considers a
game supported when `games/<steam-app-id>/game.json` exists and passes all
integrity checks.

No real games or mods are included in the initial catalog.

Set the repository variable `OFFICIAL_REVIEWERS` to a comma-separated list of
maintainer GitHub usernames and require the catalog workflow plus CODEOWNERS
approval in branch protection. A pull request that newly sets `official: true`
then fails until one of those maintainers approves it.

See [Adding a game](docs/adding-a-game.md) and the JSON Schemas in `schemas/`.
Contributors must also follow [CONTRIBUTING.md](CONTRIBUTING.md), including its
verification and automated-assistance disclosure requirements.
