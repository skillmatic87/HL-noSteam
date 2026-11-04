# HL-noSteam

A downloadable **Counter-Strike 1.5 dedicated server package for Windows LAN games with 32 player slots**.

**Status: preview installer available; client acceptance tests remain open.** A fresh installation starts with 32 slots, StatsMe, bots, the admin plugins, Map Manager and Sank Sounds. This is not yet a fully accepted release.

## Install the preview

1. [Download the repository ZIP](https://github.com/skillmatic87/HL-noSteam/archive/refs/heads/main.zip) and extract it into a writable folder.
2. Run `Setup.cmd`. The first setup downloads about 300 MB of original components and verifies every file against its SHA-256 checksum.
3. Enter your game rules and administrator player name. Yes/no questions accept `yes`/`y` or `no`/`n`; empty or invalid answers ask again. The original server license is included as a file, without an interactive license prompt.
4. Open `CS15Server/ADMIN.local.txt` for your unique administrator credentials.
5. Run `CS15Server/Start-CS15.cmd` and connect using a compatible CS 1.5 client on the LAN.

Setup requires 64-bit Windows with PowerShell 5.1, `curl.exe` and `tar.exe`; only the current development PC has been tested. It installs into a new `CS15Server` folder and refuses to overwrite an existing server. If configuration is interrupted before settings are saved, rerun `Setup.cmd` to continue with the prepared files. Initial setup needs Internet access; later setup attempts can reuse verified cached downloads. It does not install a game client or change firewall settings.

See [installation and operation](docs/INSTALL.md) for commands, configuration, cached setup and remaining test limitations. This preview downloads third-party files from their recorded sources; it is not a fully offline ZIP containing all game binaries.

The additional LAN pack installs **13 custom maps, including `de_rats_2001`, `awp_map`, `fy_iceworld` and `fy_pool_day`, plus 28 selected chat sounds**. See [content, commands and existing-server updates](docs/CONTENT.md). Open [the offline listening page](content/Listen.html) to preview the new sounds. Existing default installations can use `Update-Content.cmd` after stopping the server.

## First release

The package should be easy to install by downloading, extracting and copying files. It must include:

- CS 1.5 dedicated server configuration for Windows and LAN play.
- 32 configured player slots.
- StatsMe and a persistent ranking stored on this server.
- A map vote five minutes before the map ends, with player nominations.
- Maps and bots.
- An admin menu restricted to authenticated administrators.
- Chat-triggered sounds audible to all players.

The installer assembles existing server mods and compiles the two Pawn plugins using the included upstream AMXX compiler. The only plugin source adaptation changes Map Manager's new-round event for CS 1.5. StatsMe uses its original, unmodified CS-specific 2.7.0 binary.

## Project documents

- [Delivery requirements and acceptance checks](docs/DELIVERY.md)
- [Installation and operation](docs/INSTALL.md)
- [Local client widescreen profiles and LAN connection](docs/CLIENT.md)
- [Implementation plan](docs/PLAN.md)
- [Open questions](docs/OPEN-QUESTIONS.md)
- [Sources and compatibility notes](docs/SOURCES.md)
- [Integration test results and limitations](docs/TESTING.md)
- [Read-only Half-Life inventory script](scripts/Get-HalfLifeInventory.ps1)

All project documentation, filenames, comments and messages are maintained in English.

## Initial local inventory

The existing Half-Life installation reports **1.1.0.8**, confirmed by the Windows file version of `hl.exe` and the supplied `readme.txt`. It contains `hlds.exe`, `valve`, `tfc` and `dmc`; no `cstrike` directory was present during the initial inventory. File inspection did not establish a running engine build.

Research downloads and test installations are kept outside the tracked project files. Credentials, operator logs, saved rankings and private configuration are not published.
