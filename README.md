# HL-noSteam

A downloadable **Counter-Strike 1.5 dedicated server package for Windows LAN games with 32 player slots**.

**Status: in development. No ready-to-use server package has been released yet.** An isolated test server starts with 32 slots, StatsMe, bots, the admin plugins, Map Manager and Sank Sounds. Client acceptance tests and release packaging remain open.

## First release

The package should be easy to install by downloading, extracting and copying files. It must include:

- CS 1.5 dedicated server configuration for Windows and LAN play.
- 32 configured player slots.
- StatsMe and a persistent ranking stored on this server.
- A map vote five minutes before the map ends, with player nominations.
- Maps and bots.
- An admin menu restricted to authenticated administrators.
- Chat-triggered sounds audible to all players.

Existing server mods will be assembled and configured. The complete server distribution can be included where its applicable distribution terms permit this. Packaging and compatibility checks are ongoing.

## Project documents

- [Delivery requirements and acceptance checks](docs/DELIVERY.md)
- [Implementation plan](docs/PLAN.md)
- [Open questions](docs/OPEN-QUESTIONS.md)
- [Sources and compatibility notes](docs/SOURCES.md)
- [Integration test results and limitations](docs/TESTING.md)
- [Read-only Half-Life inventory script](scripts/Get-HalfLifeInventory.ps1)

All project documentation, filenames, comments and messages are maintained in English.

## Initial local inventory

The existing Half-Life installation reports **1.1.0.8**, confirmed by the Windows file version of `hl.exe` and the supplied `readme.txt`. It contains `hlds.exe`, `valve`, `tfc` and `dmc`; no `cstrike` directory was present during the initial inventory. File inspection did not establish a running engine build.

Research downloads and test installations are kept outside the tracked project files. Credentials, operator logs, saved rankings and private configuration are not published.
