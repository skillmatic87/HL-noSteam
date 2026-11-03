# Installation and operation

## Preview status

The installer has been tested in a new folder independently of the existing Half-Life game installation. Server startup, plugin loading, map changes and bot gameplay work. Human-client connection, permission enforcement and audible chat sounds still require acceptance testing. See [test results](TESTING.md).

## Download and setup

Download the repository ZIP from GitHub, extract it, and run `Setup.cmd`. Use a writable folder with sufficient space for the downloaded archives, extracted originals and installed server. Keep the extracted files together.

The default destination is `CS15Server` beside `Setup.cmd`. Setup downloads the exact files in [components.json](../scripts/components.json), checks SHA-256, extracts the original HLDS installer, displays its license, installs the server and mods, and asks for your configuration. The existing Half-Life installation is not a prerequisite.

All first-time downloads require Internet access. Verified archives remain in `downloads/packages`; retain that folder to reuse them. No third-party binary is stored in this Git repository. The original HLDS installer is retained in the installed `_setup` directory, along with extracted source material and notices. The source archives are retained in the download cache.

To choose a different destination or an existing verified cache:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Install-CS15Server.ps1 -Destination D:\CS15Server -CacheDirectory D:\CS15Downloads
```

The destination must not already exist. If setup fails, inspect the error and the `.install-incomplete` marker before choosing a fresh destination. Setup does not delete or overwrite an old installation. A checksum mismatch stops setup; move the incorrect cached file aside before retrying.

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
| `cstrike/addons/statsme/statsme.log` | Binary persistent ranking; keep it when moving the server |
| `cstrike/addons/yapb/conf/yapb.cfg` | Bot fill target and difficulty |

Keep credentials private. The repository ignores these local configuration files and generated game data. Configuration can be edited locally after stopping the server; setup is not an updater and does not merge existing configuration.

## Start and connect

Run `Start-CS15.cmd`. The dedicated server uses UDP port 27015 and LAN mode. In a compatible CS 1.5 client, use `connect <server-LAN-address>:27015`; on the same PC, use `connect 127.0.0.1:27015`. Allow the game's LAN traffic in the firewall yourself if needed. No Internet port forwarding is needed for LAN play.

Configure the exact administrator player name and the private `setinfo _pw` value from `ADMIN.local.txt` before connecting. After connecting, `amxmodmenu` opens the stock AMXX menu. The independent StatsMe password menu is disabled, and no shared public administrator password is installed.

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
