# HL-noSteam

A downloadable **Counter-Strike 1.5 dedicated server package for Windows LAN games with 32 player slots**.

**Linux Mint:** the experimental installer is maintained in the [linux-mint-server branch](https://github.com/skillmatic87/HL-noSteam/tree/linux-mint-server). See its [setup and verification guide](https://github.com/skillmatic87/HL-noSteam/blob/linux-mint-server/docs/LINUX-MINT.md).

**Status: release candidate; remaining acceptance checks are documented.** A fresh installation starts with 32 slots, StatsMe, bots, the admin plugins, Map Manager and Sank Sounds. Startup, administrator access, map changes/votes, sounds, custom-map downloads and bot play have been reported working. Ranking persistence, simultaneous sounds with two human clients and a 32-client load test remain open. See [test results](docs/TESTING.md).

## Start here

Keep the extracted package together. The important Windows entry points are directly in its main folder:

| File | Purpose |
| --- | --- |
| [Setup.cmd](Setup.cmd) | Install the server; run this first. |
| [Start-Server.cmd](Start-Server.cmd) | Start the installed server in its console. |
| [Start-Panel.cmd](Start-Panel.cmd) | Open the local panel to configure, start and stop the server. Requires Python 3.10+. |
| [Configure-Server.html](Configure-Server.html) | Read-only preview and portable profiles when opened directly. |
| [Update-Content.cmd](Update-Content.cmd) | Update maps, sounds and shared presentation on an existing default installation. |

The Linux branch/package supplies the matching `Setup-Linux.sh`, `Start-Server.sh` and `Start-Panel.sh` in its main folder; run them with `bash`.

## Install

1. [Download the repository ZIP](https://github.com/skillmatic87/HL-noSteam/archive/refs/heads/main.zip) and extract it into a writable folder.
2. Run `Setup.cmd`. The first setup downloads about 300 MB of original components and verifies every file against its SHA-256 checksum.
3. Enter your game rules and administrator player name. Yes/no questions accept `yes`/`y` or `no`/`n`; empty or invalid answers ask again. The original server license is included as a file, without an interactive license prompt.
4. Open `CS15Server/ADMIN.local.txt` for your unique administrator credentials.
5. Run `Start-Server.cmd` from the main folder, or open `Start-Panel.cmd` and use **Start server**. Connect using a compatible CS 1.5 client on the LAN.

Setup requires 64-bit Windows with PowerShell 5.1, `curl.exe` and `tar.exe`; only the current development PC has been tested. It installs into a new `CS15Server` folder and refuses to overwrite an existing server. If configuration is interrupted before settings are saved, rerun `Setup.cmd` to continue with the prepared files. Initial setup needs Internet access; later setup attempts can reuse verified cached downloads. It does not install a game client or change firewall settings.

See [installation and operation](docs/INSTALL.md) for commands, configuration, cached setup and remaining test limitations. This preview downloads third-party files from their recorded sources; it is not a fully offline ZIP containing all game binaries.

The additional LAN pack installs **13 custom maps, including `de_rats_2001`, `awp_map`, `fy_iceworld` and `fy_pool_day`, plus 108 chat sounds**. The sound pack includes 80 further clips selected by the operator. Together with the 14 original sounds, installations have 122 chat commands. See [content, commands and existing-server updates](docs/CONTENT.md). Open [the offline listening page](content/Listen.html) to preview the additional sounds. Existing default installations can use `Update-Content.cmd` after stopping the server.

The shared pack also supplies a welcome MOTD with player commands and the repository link, `welcome.wav` on joins, and **838 selectable English bot-chat messages** in the classic LAN style. Bots occasionally mention the repository and can reply with Windows and experimental Linux Mint installation links. Chat frequency keeps the YaPB default. See [welcome screen, bot chat and update protection](docs/CONTENT.md#welcome-screen-and-bot-chat).

## Offline configuration

Run [Start-Panel.cmd](Start-Panel.cmd) on Windows for the local browser panel (Python 3.10+). Its loopback helper reads and saves configuration and starts/stops the local server. Edit maps by drag-and-drop, duration, slots, bots, sounds, ranking and welcome text. **Administration** manages AMX administrator names/passwords, RCON and YaPB access, with separate review and private backups. The interface supports English and German. Opening [Configure-Server.html](Configure-Server.html) directly provides read-only import and profiles. See [usage, backups and test details](docs/CONFIGURATOR.md).

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

Project documentation and scripts use English. The local panel defaults to English and offers an English/German language selector.

## Initial local inventory

The existing Half-Life installation reports **1.1.0.8**, confirmed by the Windows file version of `hl.exe` and the supplied `readme.txt`. It contains `hlds.exe`, `valve`, `tfc` and `dmc`; no `cstrike` directory was present during the initial inventory. File inspection did not establish a running engine build.

Research downloads and test installations are kept outside the tracked project files. Credentials, operator logs, saved rankings and private configuration are not published.
