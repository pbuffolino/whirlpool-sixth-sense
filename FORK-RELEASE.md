# Maintained laundry fork

The fork release channel is GitHub, not PyPI. Release tags identify immutable
source for vendoring into the separately maintained Home Assistant trial.

The initial laundry candidate combines:

- Upstream master `df3f39436a4a6078fbb2a3464a8f3ee7e37f7bca`.
- Washer PR [abmantis#224](https://github.com/abmantis/whirlpool-sixth-sense/pull/224),
  head `f29c2a2b9a99c743d4022ac551c8a54562079cc0`.
- Dryer PR [abmantis#194](https://github.com/abmantis/whirlpool-sixth-sense/pull/194),
  head `50d6efa0a7fa8bd740572a05f36e532156b6bb6e`, which contains the washer head.

The fork retains local validation and its release draft workflow. Upstream CI
changes do not restore retired hosted checks. The unsupported FabricCare test
follows master #229: generic unsupported appliances remain discoverable, without
being classified as a washer or dryer.

## Updating and releasing

1. Verify `fork` points to `pbuffolino/whirlpool-sixth-sense` and `origin` to
   `abmantis/whirlpool-sixth-sense`. Fetch upstream master and the selected PR
   heads. Record their full commits. Never write to upstream without approval.
2. Create an ignored `.worktrees/<task>` branch from `fork/master`. Merge upstream
   master, preserving this fork's local-check and no-PyPI-publisher policy. Merge
   only still-needed laundry changes, accounting for already merged ancestors.
3. Install `requirements-dev.txt` in isolated Python 3.14+, commit, then run
   `bash scripts/check-local.sh` from the clean candidate with that environment
   active. Fix failures and rerun after source changes.
4. Obtain separate independent native Codex code and security reviews of the exact
   candidate. Open a proper PR against this fork's master with checks, versions
   and review dispositions, recheck its head, then merge.
5. For an authorized release, tag the reviewed merged source with the next unused
   fork tag, for example `2.0.3+laundry.1`, and publish a GitHub release pointing
   to that exact commit. Verify the remote tag and record both tag and commit.
   Do not upload this fork under the upstream PyPI package name.
6. Re-vendor the exact tag in home-observability using its vendor script; record
   the fork URL, tag, commit and file hashes in `PROVENANCE.json`. Run its full
   local check and independent reviews. Follow its copy/restart approval,
   rollback and six-sensor acceptance procedure. A source release does not prove
   Home Assistant installation or live appliance-cycle behavior.

## Returning to Home Assistant core

Check the actual installed Core release's Whirlpool manifest and laundry entity
support. Switch only after its released library and integration provide the
required washer/dryer sensors and read-only behavior. Plan entity-ID, Assist/MCP
and automation continuity, obtain the required maintenance approval, disable the
trial entry, and verify the trial worker stops before configuring core. Preserve
a rollback copy and verify both appliances through a natural cycle. Do not
replace core's `whirlpool` domain or clear unrelated MQTT discovery entities.
