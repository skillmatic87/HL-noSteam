# Implementation plan

A downloaded component is not a verified working integration. This plan separates agreed requirements, downloaded candidates and runtime checks.

## 1. Establish the Windows server base

The initial local Half-Life installation reports 1.1.0.8. Build and test the first server package in a separate directory: **CS 1.5, Windows, LAN, 32 slots**.

The original **HLDS 4.1.1.0** installer and archived **CS 1.5** mod with its 26 original maps have been downloaded. The installer matches the size and MD5 recorded by separate archive listings. Its files were extracted for inspection without running the historical installer. Record hashes and exact source revisions before packaging.

Review the license supplied with the actual server package. Its distribution provisions concern exact copies with accompanying files and notices; account for this when choosing an original installer, installation overlay or ready-to-run directory. Do not substitute today's Steam engine without compatibility checks.

## 2. Assemble existing plugins

| Feature | Existing component being evaluated | Current evidence |
| --- | --- | --- |
| GoldSrc plugin loader | Metamod-P 1.21p109 | Loads the selected Windows plugins |
| Statistics and local ranking | StatsMe 2.7.0, original CS-specific build | Records damage, shots, hits and kills; ranking records survive a process restart unchanged |
| Admin menu | AMX Mod X 1.8.1 | Stock admin/menu plugins load; client permission checks pending |
| Votes and nominations | Mistrick Map Manager 2.5.61 | Compiles with a small CS 1.5 round-event adaptation; five-minute setting active |
| Chat sounds | Sank Sounds 1.9.1 | Compiles and loads 14 classic StatsMe sound-pack entries; client playback pending |
| Bots | YaPB 4.4.957 | Two test bots join and play on de_dust and de_dust2 |

Use one active map-vote system. Avoid duplicate menus or overlapping statistics commands. Prefer configuring existing components. Document any narrow compatibility or timing adjustment rather than replacing an existing mod.

The researched WON2 project's FAQ calls for AMXX 1.8.2 or older, while the official AMXX 1.8.2 notes describe changes for the 2013 server update. Neither proves that every module works with CS 1.5; 1.8.1 is being evaluated. Linux container instructions are research context, not the agreed deployment.

## 3. Configure the agreed behavior

- LAN mode and 32 slots.
- Automatic vote five minutes before map end, including nominations.
- Authenticated admin menu and privileged commands.
- Persistent ranking saved on this server.
- Chat sounds heard by all players.
- Maps, resources and bot navigation data available.

Unanswered preferences remain in [open questions](OPEN-QUESTIONS.md). Test-only values must be identified as such. Retain the existing local client while preparing the standalone test server.

## 4. Package for download and copying

Prepare a versioned Windows download with English instructions, launch/configuration files, required existing mods, notices and source material required by component licenses. Preserve original installers where their terms require that form. Exclude credentials and generated rankings.

Test the package after fresh extraction. Configuration fragments alone are not the final deliverable.

The rejected StatsMe 2.8.3 build mishandles the old engine's absolute game directory. The original CS-specific 2.7.0 binary uses the fixed mod name `cstrike`, avoiding that regression without a custom StatsMe patch. A fresh installation under a long directory path loads successfully. See [test results](TESTING.md).

The preview installer now downloads pinned components, verifies checksums, assembles a new server, compiles the existing Pawn plugins and configures local credentials. It includes all 26 original maps and downloads the two missing YaPB graph files. It has passed a fresh-folder installation test; packaging the final offline distribution and human-client acceptance remain open.

## 5. Verify the result

Follow [acceptance checks](DELIVERY.md). Record tested versions, outcomes and unavailable test environments. Do not claim 32-client load testing, a second-PC LAN connection or multi-client audio without performing those checks.

## Broader project

Half-Life Deathmatch and other platforms remain possible later work. A website or cross-server leaderboard is outside the clarified ranking requirement.
