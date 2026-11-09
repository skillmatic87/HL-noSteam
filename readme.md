# Half-Life Counter-Strike 1.5 Server Linux

A native **Counter-Strike 1.5 Non-Steam dedicated server package for Linux Mint LAN games with 32 player slots**.

**Linux Mint:** this branch also includes the native Linux installer and launchers. See [Linux Mint setup and verification](docs/linux-mint.md). Install the documented 32-bit dependencies, then run `bash setup-linux.sh`. Initial startup, client connection and administrator access have been reported working; further acceptance checks remain open.

**Version 1.1.2.** A fresh installation starts with 32 slots, StatsMe, bots, the admin plugins, Map Manager and Sank Sounds. Startup, administrator access, map changes/votes, sounds, custom-map downloads and bot play have been reported working. Ranking persistence, simultaneous sounds with two human clients, native Mint/GNOME console behavior and a 32-client load test remain open. See [test results](docs/testing.md).

Linux server starts now always record the console in a separate timestamped `logs/console/` file inside the installed server. See [permanent console recording](docs/linux-mint.md#permanent-console-recording). Maintained package filenames are lowercase; use `bash start-panel.sh` or `bash start-server.sh`. See [updating older ZIPs](docs/updating.md) before the first update to this version.

## Separate Steam and Non-Steam repositories

| Edition | Repository | Platforms and source branch |
| --- | --- | --- |
| Counter-Strike 1.5 Non-Steam | [HL-noSteam](https://github.com/skillmatic87/HL-noSteam) | Windows: `main`; Linux Mint: `linux-mint-server` |
| Counter-Strike 1.6 Steam | [Counter-Strike-1.6-Steam-Server-Linux](https://github.com/skillmatic87/Counter-Strike-1.6-Steam-Server-Linux) | Linux Mint: `main` |

These are separate server packages. CS 1.5 uses the historical WON/LAN server and compatible clients. CS 1.6 uses SteamCMD, Steam clients and Steam-ID administration. Install each in its own directory; their engines, administrators and ranking files are not interchangeable. The Steam package currently supplies a Linux installer only.

The Non-Steam repository keeps its historical `HL-noSteam` URL and ZIP folder names to preserve the archive identity expected by Linux package updaters. Follow the package update instructions when upgrading older ZIPs.

## Start here

Keep the extracted package together. The important Windows entry points are directly in its main folder:

| File | Purpose |
| --- | --- |
| [setup.cmd](setup.cmd) | Install the server; run this first. |
| [start-server.cmd](start-server.cmd) | Start the installed server in its console. |
| [start-panel.cmd](start-panel.cmd) | Open the local panel to configure, start and stop the server. Requires Python 3.10+. |
| [configure-server.html](configure-server.html) | Read-only preview and portable profiles when opened directly. |
| [update-content.cmd](update-content.cmd) | Update maps, sounds and shared presentation on an existing default installation. |

On Linux, this branch supplies the matching `setup-linux.sh`, `start-server.sh` and `start-panel.sh` in the main folder; run them with `bash`.

For an existing Linux ZIP package, stop the server/panel helper and run `bash update.sh`. See [updating and versioned downloads](docs/updating.md), including the one-time script download for older packages.

## Install on Linux

Follow [Linux setup and dependencies](docs/linux-mint.md), download the [Linux branch ZIP](https://github.com/skillmatic87/HL-noSteam/archive/refs/heads/linux-mint-server.zip), then run `bash setup-linux.sh` and `bash start-server.sh`.

## Install on Windows

1. [Download the repository ZIP](https://github.com/skillmatic87/HL-noSteam/archive/refs/heads/main.zip) and extract it into a writable folder.
2. Run `setup.cmd`. The first setup downloads about 300 MB of original components and verifies every file against its SHA-256 checksum.
3. Confirm the suggested rules with `y`/`n` (also accepting `j`/`n`), or enter custom values. The map-time suggestion is 20 minutes. Enter your administrator name and three separate passwords for AMX, YaPB and RCON; password entry is hidden and confirmed. See [all setup questions](docs/setup.md). The original server license is included as a file, without an interactive license prompt.
4. Open `CS15Server/ADMIN.local.txt` for your unique administrator credentials.
5. Run `start-server.cmd` from the main folder, or open `start-panel.cmd` and use **Start server**. Connect using a compatible CS 1.5 client on the LAN.

Setup requires 64-bit Windows with PowerShell 5.1, `curl.exe` and `tar.exe`; only the current development PC has been tested. It installs into a new `CS15Server` folder and refuses to overwrite an existing server. If configuration is interrupted before settings are saved, rerun `setup.cmd` to continue with the prepared files. Initial setup needs Internet access; later setup attempts can reuse verified cached downloads. It does not install a game client or change firewall settings.

See [installation and operation](docs/install.md) for commands, configuration, cached setup and remaining test limitations. This package downloads third-party files from their recorded sources; it is not a fully offline ZIP containing all game binaries.

The additional LAN pack installs **13 custom maps, including `de_rats_2001`, `awp_map`, `fy_iceworld` and `fy_pool_day`, plus 108 chat sounds**. The sound pack includes 80 further clips selected by the operator. Together with the 14 original sounds, installations have 122 chat commands. See [content, commands and existing-server updates](docs/content.md). Open [the offline listening page](content/listen.html) to preview the additional sounds. Existing default installations can use `update-content.cmd` after stopping the server.

The shared pack also supplies a welcome MOTD with player commands and the repository link, `welcome.wav` on joins, and **838 selectable English bot-chat messages** in the classic LAN style. Bots occasionally mention the repository and can reply with Windows and experimental Linux Mint installation links. Chat frequency keeps the YaPB default. See [welcome screen, bot chat and update protection](docs/content.md#welcome-screen-and-bot-chat).

## Offline configuration

Run [start-panel.cmd](start-panel.cmd) on Windows for the local browser panel (Python 3.10+). Its loopback helper reads and saves configuration and starts/stops the local server. Edit maps by drag-and-drop, duration, slots, bots, sounds, ranking and welcome text. **Administration** manages AMX administrator names/passwords, RCON and YaPB access, with separate review and private backups. The interface supports English and German. Opening [configure-server.html](configure-server.html) directly provides read-only import and profiles. See [usage, backups and test details](docs/configurator.md).

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

- [Delivery requirements and acceptance checks](docs/delivery.md)
- [Installation and operation](docs/install.md)
- [Local client widescreen profiles and LAN connection](docs/client.md)
- [Implementation plan](docs/plan.md)
- [Open questions](docs/open-questions.md)
- [Sources and compatibility notes](docs/sources.md)
- [Integration test results and limitations](docs/testing.md)
- [Read-only Half-Life inventory script](scripts/get-halflifeinventory.ps1)

Project documentation and scripts use English. The local panel defaults to English and offers an English/German language selector.

## Initial local inventory

The existing Half-Life installation reports **1.1.0.8**, confirmed by the Windows file version of `hl.exe` and the supplied `readme.txt`. It contains `hlds.exe`, `valve`, `tfc` and `dmc`; no `cstrike` directory was present during the initial inventory. File inspection did not establish a running engine build.

Research downloads and test installations are kept outside the tracked project files. Credentials, operator logs, saved rankings and private configuration are not published.
