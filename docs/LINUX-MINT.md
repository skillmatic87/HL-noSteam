# Native CS 1.5 server for Linux Mint

**Status: experimental. Archive assembly is verified on Windows. On 2026-11-04, the operator reported successful Linux startup, a Windows client connection and working administrator access. YaPB in-game configuration was denied because of missing permissions.** See [operator-reported results and remaining checks](TESTING.md#operator-reported-linux-checks-2026-11-04). Development lives in the `linux-mint-server` branch. Windows keeps its existing `Setup.cmd` installer. Further Mint acceptance checks remain before merging platform support into `main`, keeping maps, sounds and shared component versions in one repository.

This installer targets an x86-64 Linux Mint computer with 32-bit compatibility libraries. It installs native Linux HLDS 3.1.1.0, the counterpart to the Windows HLDS 4.1.1.0 package. It does not require Wine, SteamCMD or a local game client. ARM is not supported. A compatible CS 1.5 client is still required for playing.

## Install

Run these dependency commands on the **Mint computer**, in a terminal. Administrative rights are used only to install system packages:

```bash
sudo dpkg --add-architecture i386
sudo apt update
sudo apt install git python3 iproute2 libc6:i386 libgcc-s1:i386 libstdc++6:i386 libstdc++5:i386 zlib1g:i386
```

The old `libstdc++5` package is in Ubuntu's Universe repository. If APT cannot find it, enable Universe in Software Sources, update the package list and retry. Do not replace old library names with symlinks to incompatible versions. [Ubuntu package details](https://packages.ubuntu.com/noble/libstdc%2B%2B5).

Then, as your regular user:

```bash
git clone --branch linux-mint-server --single-branch https://github.com/skillmatic87/HL-noSteam.git
cd HL-noSteam
bash Setup-Linux.sh
bash Start-Server.sh
```

All important entry points are in the extracted package's main folder: `Setup-Linux.sh`, `Start-Server.sh` and `Start-Panel.sh`. Run `bash Start-Panel.sh` for the English/German browser control panel, including drag-and-drop rotation and AMX/RCON/YaPB access settings. It requires Python 3.10+; the generated `CS15Server-Linux/Start-CS15.sh` launcher remains available. Keep the package files together. A custom installation is selected with `bash Start-Server.sh /path/to/server` or `bash Start-Panel.sh /path/to/server`.

Alternatively, download the [branch ZIP](https://github.com/skillmatic87/HL-noSteam/archive/refs/heads/linux-mint-server.zip), extract it, open a terminal in the extracted directory and run `bash Setup-Linux.sh`. Using `bash` works even when ZIP extraction did not preserve executable permissions.

Setup asks for the same game rules and administrator name as Windows. It generates separate private admin and RCON credentials in `CS15Server-Linux/ADMIN.local.txt`. Yes/no answers accept `yes`/`y` and `no`/`n`. No unanswered gameplay preferences are filled in automatically.

Downloads are SHA-256 verified and cached in `downloads/linux`. A first installation needs Internet access. The server, extracted upstream source material and notices remain in the new server directory; keep the download cache to retain the original component archives. Do not publish the configured server directory or its private credentials.

Setup selects the IPv4 address on the sole default-route adapter. With VPNs, multiple adapters or a LAN without a default route, select your assigned LAN address explicitly:

```bash
bash Setup-Linux.sh --bind-address 192.168.1.50 --destination "$HOME/CS15Server"
bash "$HOME/CS15Server/Start-CS15.sh"
```

Change the example address to an address assigned to your Mint PC. The installer checks that it can bind locally. If DHCP changes it later, update `+ip` in `Start-CS15.sh`.

Existing destination directories are refused. If installation fails after extraction, the folder keeps `.install-incomplete` and cannot start through the generated launcher. Preserve it for diagnosis and retry with a **new destination**; verified cached downloads will be reused. Linux setup does not currently implement the Windows installer's configuration-resume or content-update/rollback commands.

For unattended setup, pass `--settings /path/to/settings.local.json`, using the field names and accepted values documented in [installation and operation](INSTALL.md). The supplied JSON must contain all ten settings. Do not run setup or the server with `sudo`.

## Included behavior

- LAN mode, UDP 27015 and 32 player slots; initial map `de_dust2`.
- Metamod-P 1.21p109, AMXX 1.8.1, original CS-specific StatsMe 2.7.0 and YaPB 4.4.957, using their Linux libraries.
- Map Manager 2.5.61 with the same narrow CS 1.5 round-event adaptation and a vote five minutes before map end.
- Sank Sounds 1.9.1, 39 maps total and 122 chat-sound commands from the shared content manifest.
- Name/password administrator authentication and server-local name-based ranking with automatic resets disabled.
- Shared welcome MOTD, welcome join sound and 838 selectable English bot-chat messages, including occasional repository references and platform installation links. See [presentation and existing-installation update steps](CONTENT.md#welcome-screen-and-bot-chat).

The AMXX Pawn plugins are compiled using the Linux compiler during installation. The generated launcher runs `hlds` directly, sets its local library search path and forwards additional command-line arguments. It does not automatically restart a crashed server or install a system service.

## Fix an older installation stopping on a map change

An operator-provided console recording captured a shutdown on `de_prodigy` on 2026-11-04 at 20:41:45:

```text
FATAL ERROR (shutting down): WARNING: couldn't open valve/cstrike.wad
COMMAND_EXIT_CODE="255"
```

The pinned CS archive supplies `cstrike.WAD`, `cs_assault.WAD`, `tswad.WAD` and `itsItaly.wad`, while the maps request lowercase WAD filenames. A Windows assembly check that only uses file-existence checks hides this mismatch. The Linux installer now normalizes root WAD filenames to lowercase without modifying their contents or any BSP files. This change applies to new installations; existing installations need the following local repair.

With the server stopped, open a terminal **inside the installed `CS15Server-Linux` folder** and run:

```bash
cp -n -- cstrike/cstrike.WAD cstrike/cstrike.wad
cp -n -- cstrike/cs_assault.WAD cstrike/cs_assault.wad
cp -n -- cstrike/tswad.WAD cstrike/tswad.wad
cp -n -- cstrike/itsItaly.wad cstrike/itsitaly.wad
```

These commands retain the original files and do not overwrite existing lowercase copies. If a source file is missing or a command reports an access error, inspect the exact filenames and permissions before continuing. No new WAD download or game-server reinstall is needed when these original files are intact.

Start the server again and enter `changelevel de_prodigy` in its dedicated console. Verify that the map loads and the server continues responding. This Linux runtime check is still required; the automated regression checks actual directory-entry spelling and byte preservation on the development host. The captured WAD failure explains this particular termination, not every possible future shutdown.

## Verify on Mint

Installation uses `ldd` to check the selected Linux binaries and compiler dependencies. This dependency check does not prove that a library loads successfully inside the old engine.

1. Run `bash CS15Server-Linux/Start-CS15.sh`. Save any startup error before retrying. In the server console, run `version`, `meta list`, `amxx plugins`, `amxx modules` and `status`. Confirm the native server version, three running Metamod plugins, loaded AMXX plugins/modules and 32 slots. A missing library, `bad load`, `unknown`, crash or unresolved symbol is a failed runtime check.
2. Join from a compatible CS 1.5 client on another LAN computer: `connect <Mint-LAN-IP>:27015`. Verify that HLSW reports the same address and slot count. For an active Mint firewall, allow UDP 27015 for your actual LAN subnet; router port forwarding is not needed for this LAN setup.
3. Test bot play on `de_dust2` and a custom map. Test nominations and the automatic map vote five minutes before the configured time limit.
4. Check that an unauthenticated player cannot use the admin menu, then authenticate using the private `setinfo _pw` command and run `amxmodmenu`. YaPB bot menus require [separate authentication](INSTALL.md#yapb-in-game-administration); AMXX access alone does not grant YaPB access.
5. Have two human players test chat sounds, including living/dead players, cooldown and quota. Confirm custom map resources download and appear correctly; Linux filenames are case-sensitive.
6. Make a kill, inspect `/top15`, stop with `quit`, restart and check that the ranking persists. Preserve both possible StatsMe ranking paths described in [INSTALL.md](INSTALL.md) when backing up or migrating.

Record the Mint version, startup output and outcomes before calling this a supported release. Presence of all bot graph files does not establish navigation quality, and a configured 32-slot limit is not a 32-client load test.

## What was checked on Windows

On 2026-11-04, nine automated safety/configuration tests passed. A fresh installation was assembled from the real checksum-pinned Linux archives. The check verified the active 32-bit ELF binaries, Linux Metamod paths, 39 map files and navigation graphs, 122 sound mappings, five-minute vote configuration and successful compilation of both custom AMXX plugins. A separate Bash syntax check passed for the setup wrapper and generated launcher.

For this assembly test only, the existing Windows AMXX 1.8.1 compiler produced platform-independent Pawn bytecode. The Linux installer normally uses its bundled Linux compiler. **Neither Linux compilation nor server execution was tested on this Windows host.** There is no configured WSL distribution on this host, and no Mint VM was started.

Reproduce the offline safety tests on either platform:

```bash
python3 scripts/test_cs15_linux.py
```

With all archives present in the cache, Linux can also run the assembly check (this creates a separate test installation under `runtime`):

```bash
python3 scripts/test_cs15_linux.py --integration-cache downloads/linux
```

## Component provenance

[components-linux.json](../scripts/components-linux.json) replaces four Windows entries from the shared [components.json](../scripts/components.json). The Windows-only Wise unpacker is excluded. StatsMe's shared ZIP already includes `sm_cstrike_mm_i386.so`; the shared CS archive includes `cs_i386.so`.

- [Archived Linux HLDS originals](https://archive.org/details/goldsrc_hlds_won_linux): original `hlds_l_3110_full.tar.gz`, including `EULA.TXT`, retained unchanged in the cache. The license is also copied to `SERVER-LICENSE.txt` in the installed directory.
- [Metamod-P release](https://github.com/Bots-United/metamod-p/releases/tag/v1.21p109): Ubuntu 18.04 Linux build, with the same SHA-256 published in the release asset metadata.
- [AMXX 1.8.1 base downloads](https://sourceforge.net/projects/amxmodx/files/AMX%20Mod%20X%20Base/1.8.1/): Linux tar archive and native compiler.
- [YaPB 4.4.957](https://github.com/yapb/yapb/releases/tag/4.4.957): Linux tar archive and navigation data.

All four replacement archives were downloaded and inspected. Locally calculated checksums pin the inspected bytes; they are not independent authenticity evidence. Shared plugin sources, graph credits and content notices are retained as with Windows.
