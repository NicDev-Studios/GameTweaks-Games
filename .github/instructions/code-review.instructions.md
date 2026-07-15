---
applyTo: "**"
excludeAgent: "cloud-agent"
---

# Catalog code review instructions

- Lead with objective integrity, compatibility, security, or maintainability
  findings and cite the smallest relevant line range.
- Verify decimal Steam App IDs, directory names, referenced filenames, mod IDs,
  BepInEx GUIDs, semantic versions, runtime, architecture, and minimum Agent
  version for internal consistency.
- Verify that each game index digest matches the exact mod JSON and that each mod
  release digest is a lowercase SHA-256 for the exact stated ZIP asset.
- Flag arbitrary URLs, alternate hosts, unsafe filenames, unbounded fields,
  dependency cycles, missing dependencies, asymmetric conflicts, and duplicate
  IDs or selection values.
- Review every configuration default against its declared type, allowed values,
  bounds, step, display, and apply mode.
- Treat a new `official: true` value without the required maintainer approval as
  blocking. Official status must not change IPC permissions or trust boundaries.
- Flag fabricated, unverifiable, generic, or contradictory catalog data. Do not
  accuse contributors of using AI based on prose style. The explicit select-all
  attention checkbox being checked is an objective reason for manual review.
- Require updated schemas, examples, documentation, and validator coverage when
  the catalog contract changes.
