# Installation and operation

## Preview status

The installer has been tested in a new folder independently of the existing Half-Life game installation. Server startup, plugin loading, map changes and bot gameplay work. Human-client connection, permission enforcement and audible chat sounds still require acceptance testing. See [test results](TESTING.md).

## Download and setup

Download the repository ZIP from GitHub, extract it, and run `Setup.cmd`. Use a writable folder with sufficient space for the downloaded archives, extracted originals and installed server. Keep the extracted files together.

The default destination is `CS15Server` beside `Setup.cmd`. Setup downloads the exact files in [components.json](../scripts/components.json), checks SHA-256, extracts the original HLDS installer, preserves its license, installs the server and mods, and asks for your configuration. There is no interactive license prompt. The existing Half-Life installation is not a prerequisite.

All first-time downloads require Internet access. Verified base archives remain in `downloads/packages`, and additional map/navigation downloads remain in `downloads/content`; retain them to reuse them. Selected additional WAV clips and a generated navigation graph are included in Git; game/server executables are downloaded separately. The original HLDS installer is retained in the installed `_setup` directory, along with extracted source material and notices. Source archives remain in the download cache.

After base configuration, setup adds 13 custom maps and 28 chat sounds. See [content installation, map capacities, sound commands and rollback](CONTENT.md). An existing installation uses the separate updater after stopping the server; `Setup.cmd` still refuses to overwrite a completed installation.

To choose a different destination or an existing verified cache:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Install-CS15Server.ps1 -Destination D:\CS15Server -CacheDirectory D:\CS15Downloads
```

Yes/no questions accept only `yes`/`y` or `no`/`n`, ignoring letter case and surrounding spaces. Names, numeric ranges and ranking choices have their own validation. Empty or invalid input asks the same question again without starting over.

If setup is interrupted before configuration is saved, run `Setup.cmd` again. It recognizes prepared server files and resumes configuration without reinstalling them. This includes the older installer's failure after an empty configuration answer. Preparation interrupted before file installation also reuses verified downloads. Completed servers, edited operator settings and other partial installations are protected; setup refuses to overwrite them. A checksum mismatch stops setup; move the incorrect cached file aside before retrying.

`SERVER-LICENSE.txt` is copied unchanged from `TEMP/EULAFILE` inside the original Valve `hlserver4110.exe` installer. Removing the prompt does not remove the original file or notices. The `-AcceptServerLicense` parameter remains accepted for older scripts and has no effect.

## Configuration

Setup asks for a server name, map duration, Friendly Fire, bot target/difficulty, sound cooldown/quota, bot ranking policy, ranking score and administrator name. It does not invent answers to the remaining project questions. Automated development tests can supply these fields with `-SettingsPath` pointing to a private JSON file; that file must not be published.

The fixed requirements are LAN mode, 32 slots, the automatic map vote five minutes before map end, nominations, all 26 original maps, administrator menus, server-local persistent ranking and chat sounds heard by living and dead players. YaPB fills the chosen target player count and reduces the bot population as humans join. Every original map has a local graph file; presence does not prove navigation quality on every map.

The ranking uses player names because old LAN identities are shared or unavailable. Reusing a name reuses its statistics. Automatic rank resets are disabled; `sm_rankscore` selects the score formula. The setup wizard requires a choice between kills and kills minus deaths. Upstream Sank Sounds administrator immunity remains enabled, and its aggregate sound-duration limit remains 180 seconds per player per map.

Important local files:

| File under the installed directory | Purpose |
| --- | --- |
| `ADMIN.local.txt` | Unique generated administrator and RCON credentials, plus client instructions |
| `settings.local.json` | Operator choices, excluding generated passwords |
| `cstrike/server.cfg` | Game rules and private RCON password |
| `cstrike/addons/amxmodx/configs/users.ini` | Name/password administrator authentication |
| `cstrike/addons/amxmodx/configs/mapmanager.cfg` | Vote behavior; lead time is five minutes |
| `cstrike/addons/amxmodx/configs/SND-LIST.CFG` | Sound triggers, cooldown and quota |
| `cstrike/addons/statsme/statsme.cfg` | Statistics and ranking behavior |
| `cstrike/statsme.log` | Runtime ranking path reported by the tested CS-specific StatsMe build; keep it when moving the server |
| `cstrike/addons/statsme/statsme.log` | Ranking file also supplied by the upstream package; preserve this file too when backing up an existing server |
| `cstrike/addons/yapb/conf/yapb.cfg` | Bot fill target and difficulty |

Keep credentials private. The repository ignores these local configuration files and generated game data. Configuration can be edited locally after stopping the server; setup is not an updater and does not merge existing configuration.

## Start and connect

Run `Start-CS15.cmd`. The dedicated server uses UDP port 27015 and LAN mode. Join using HLSW or the client's Multiplayer / LAN Games list. You can also use `connect <server-LAN-address>:27015` in the game console. Allow the game's LAN traffic in the firewall yourself if needed. No Internet port forwarding is needed for LAN play.

Setup writes an explicit `+ip` LAN address into `Start-CS15.cmd`, preferring the network adapter with a gateway and excluding loopback and `169.254.*` link-local addresses. This prevents an additional TAP/VPN adapter from advertising the wrong address. Ambiguous adapter selection requires `Configure-CS15Server.ps1 -BindAddress <assigned-IPv4>`. If DHCP changes the PC's address, update `+ip` in the launcher. Use that same address in HLSW; an explicitly bound server may not answer through `127.0.0.1`.

Configure the exact administrator player name and the private `setinfo _pw` value from `ADMIN.local.txt` before connecting. After connecting, `amxmodmenu` opens the stock AMXX menu. The independent StatsMe password menu is disabled, and no shared public administrator password is installed.

For HLSW administration, select the server, open **Admin > Rcon Konfiguration**, enter the **Server-console RCON password** from `ADMIN.local.txt`, and click **Testen**. **Hole Protokoll (LAN)** enables live log output. Commands in HLSW's console do not need an additional `rcon` prefix.

`ADMIN.local.txt` is a reference sheet, not an active configuration file. Changing its text does not change authentication. Set the actual `rcon_password` in `cstrike/server.cfg` and reload it with `exec server.cfg` from the dedicated console, or restart the server. Then update the reference sheet and HLSW's saved password. The AMXX administrator password is separate from RCON.

## Player commands

| Location | Command | Purpose |
| --- | --- | --- |
| Chat | `maps` or `/maps` | Open the nomination map menu |
| Chat | A map name such as `de_dust2` | Nominate that map if eligible |
| Chat | `nextmap`, `timeleft`, `currentmap` | Map information |
| Chat | `rtv` or `/rtv` | Existing Map Manager rock-the-vote feature |
| Chat | `/top15`, `/statsme`, `/stats` | StatsMe ranking and statistics |
| Client console | `amx_sound_help` | List sound triggers |
| Chat | `headshot`, `firstblood`, `doublekill` | Examples of sound triggers |

The 14 installed triggers are `dominating`, `doublekill`, `firstblood`, `godlike`, `headshot`, `humiliation`, `killingspree`, `monsterkill`, `multikill`, `perfect`, `prepare`, `rampage`, `ultrakill` and `unstoppable`.

Stop the server with `quit` in its dedicated console. Back up the stopped installation, especially its local configuration and saved ranking, before moving or replacing it.
