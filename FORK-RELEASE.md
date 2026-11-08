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
   fork tag, for example `2.1.1+laundry.1`, and publish a GitHub release pointing
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

## Dependency and security maintenance (November 8, 2026)

PyPI JSON metadata was checked for every direct runtime/development dependency.
The tested environment resolves aiohttp 3.14.5, paho-mqtt 2.2.0, aioconsole 0.8.2,
aiointercept 1.0.0, pytest 9.2.0, pytest-asyncio 1.4.1.post1, pytest-cov 7.1.0,
pytest-mock 3.17.0, Ruff 0.17.4, basedpyright 1.40.2 and prek 0.5.10. Sources:
[PyPI aiohttp](https://pypi.org/pypi/aiohttp/json),
[PyPI paho-mqtt](https://pypi.org/pypi/paho-mqtt/json), and each package's
corresponding `/pypi/<name>/json` metadata. `pip-audit` 2.10.1 reported no known
vulnerabilities in the resolved environment. This is an advisory-database
snapshot, not proof that the library or all allowed historical versions are safe.

Runtime metadata and requirements now agree on aiohttp >=3.14.5,<4 and
paho-mqtt >=2.1.0,<3. The latter preserves compatibility with HA's 2.1.0 while
allowing the tested 2.2.0. The standalone websockets dependency was unused:
HTTP WebSockets use aiohttp, and MQTT WebSockets are implemented inside paho.
It was removed rather than upgrading an unused package. Development dependency
floors were raised to the tested versions; upstream's pinned analysis hooks stay.
The Python >=3.14 requirement remains because the library uses 3.14 syntax.
No broad API/style refactor was needed or attempted.

Security review identified inherited raw AWS IoT logging, credential redirects,
unbounded broker-directed capability downloads, and permissive opt-in auth-cache
storage. The release addresses these with fixed diagnostics, redirect refusal,
bounded HTTPS capability retrieval, and private atomic cache writes. Auth caching
remains opt-in; Home Assistant uses `store=False`. Existing caches with unsafe
permissions must be repaired by their owner or regenerated before loading.

Fork issue search found no existing issue; creation returned GitHub HTTP 410
because this fork disables issues. This section is the local issue draft, tracked
with fork PR #2 and home-observability #193. Observed impact is source exposure,
not an incident. Acceptance requires synthetic denial/privacy regressions and
separate exact-head code/security reviews. No runtime deployment is implied.

Capability downloads retain the existing trial's HTTPS hostname suffix policy:
`.amazonaws.com`, `.whrcloud.com`, `.applianceconnect.net`, `.cloudfront.net`.
The actual delivery hostname has not been captured, so no exact-origin claim is
made. AWS and CloudFront are shared tenant domains; this policy bounds destinations
but does not establish tenant ownership. Redirects, URL credentials, nonstandard
ports and fragments are refused. A 10-second total timeout and 2 MiB decompressed
body limit bound each attempt. Tighten to exact provider hosts when sanitized
hostname evidence becomes available, with compatibility tests before release.

The legacy HTTP backend also logged the WebSocket CONNECT frame, containing the
access token, plus incoming frames, owned-device data and command payloads. Those
logs are now fixed operational messages, with token/frame regression coverage.
HTTP command POSTs also refuse redirects so a 307/308 cannot replay device data.
