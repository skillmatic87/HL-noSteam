# Installation and operation

## Release status

The installer has been tested in a new folder independently of the existing Half-Life game installation. Server startup and plugin loading passed automated integration checks. The operator additionally reports client connections, administrator access, permission enforcement, map changes/votes, sounds, fresh-client custom maps and bot play working. Remaining acceptance checks include ranking persistence, simultaneous playback with two human clients and 32-client capacity. See [test results](TESTING.md).

## Download and setup

Download the repository ZIP from GitHub, extract it, and run `Setup.cmd`. Use a writable folder with sufficient space for the downloaded archives, extracted originals and installed server. Keep the extracted files together.

The default destination is `CS15Server` beside `Setup.cmd`. Setup downloads the exact files in [components.json](../scripts/components.json), checks SHA-256, extracts the original HLDS installer, preserves its license, installs the server and mods, and asks for your configuration. There is no interactive license prompt. The existing Half-Life installation is not a prerequisite.

After setup, the main folder contains the entry points you need: **Start-Server.cmd** opens the server console and **Start-Panel.cmd** opens the browser control panel. Keep `scripts`, `content` and the generated `CS15Server` folder beside them; these launchers work relative to the package location. The panel requires Python 3.10+. Directly opening `Configure-Server.html` only provides a preview. See [panel controls and administration](CONFIGURATOR.md).

For a custom installation location, use `Start-Server.cmd -ServerDirectory "D:\YourServer"` or `Start-Panel.cmd -ServerDirectory "D:\YourServer"`. The original `CS15Server/Start-CS15.cmd` launcher remains available as well. Running `Start-Server.cmd -WhatIf` checks the chosen installation without starting HLDS.

All first-time downloads require Internet access. Verified base archives remain in `downloads/packages`, and additional map/navigation downloads remain in `downloads/content`; retain them to reuse them. Selected additional WAV clips and a generated navigation graph are included in Git; game/server executables are downloaded separately. The original HLDS installer is retained in the installed `_setup` directory, along with extracted source material and notices. Source archives remain in the download cache.

After base configuration, setup adds 13 custom maps and 108 chat sounds, including 80 further operator-selected clips. See [content installation, map capacities, sound commands and rollback](CONTENT.md). An existing installation uses the separate updater after stopping the server; `Setup.cmd` still refuses to overwrite a completed installation.

To choose a different destination or an existing verified cache:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Install-CS15Server.ps1 -Destination D:\CS15Server -CacheDirectory D:\CS15Downloads
```

Server names support 1-63 printable ASCII characters; administrator/player names remain limited to 1-31. Overlong input reports its actual length and the applicable limit. If setup is waiting at an older name prompt, press Ctrl+C and rerun Setup.cmd from the same folder after updating these scripts; prepared server files are retained.

The English wizard displays `[y/n]` and accepts `y`/`yes`/`j`/`ja` or `n`/`no`/`nein`, ignoring case and surrounding spaces. Answer yes to confirm a proposed value, or no to enter a custom value. Map time is proposed as 20 minutes. Empty or invalid input repeats the question. See [all fourteen questions](SETUP.md).

If setup is interrupted before configuration is saved, run `Setup.cmd` again. It recognizes prepared server files and resumes configuration without reinstalling them. This includes the older installer's failure after an empty configuration answer. Preparation interrupted before file installation also reuses verified downloads. Completed servers, edited operator settings and other partial installations are protected; setup refuses to overwrite them. A checksum mismatch stops setup; move the incorrect cached file aside before retrying.

`SERVER-LICENSE.txt` is copied unchanged from `TEMP/EULAFILE` inside the original Valve `hlserver4110.exe` installer. Removing the prompt does not remove the original file or notices. The `-AcceptServerLicense` parameter remains accepted for older scripts and has no effect.

## Configuration

Setup asks for the server rules and administrator name, then hidden, confirmed AMX, YaPB and RCON passwords. Disabling bots skips their count and difficulty questions. Unattended setup can still use `-SettingsPath` with the ten public choices; it generates three separate private passwords without prompting. Passwords are never included in saved public settings JSON. Existing configured servers are not reconfigured by setup.

The fixed requirements are LAN mode, 32 slots, the automatic map vote five minutes before map end, nominations, all 26 original maps, administrator menus, server-local persistent ranking and chat sounds heard by living and dead players. YaPB fills the chosen target player count and reduces the bot population as humans join. Every original map has a local graph file; presence does not prove navigation quality on every map.

The ranking uses player names because old LAN identities are shared or unavailable. Reusing a name reuses its statistics. Automatic rank resets are disabled; `sm_rankscore` selects the score formula. The setup wizard requires a choice between kills and kills minus deaths. Upstream Sank Sounds administrator immunity remains enabled, and its aggregate sound-duration limit remains 180 seconds per player per map.

Important local files:

| File under the installed directory | Purpose |
| --- | --- |
| `ADMIN.local.txt` | Private AMX, YaPB and RCON credentials, plus client instructions |
| `settings.local.json` | Ten public operator choices, excluding passwords |
| `cstrike/server.cfg` | Game rules and private RCON password |
| `cstrike/addons/amxmodx/configs/users.ini` | Name/password administrator authentication |
| `cstrike/addons/amxmodx/configs/mapmanager.cfg` | Vote behavior; lead time is five minutes |
| `cstrike/addons/amxmodx/configs/SND-LIST.CFG` | Sound triggers, cooldown and quota |
| `cstrike/addons/statsme/statsme.cfg` | Statistics and ranking behavior |
| `cstrike/statsme.log` | Runtime ranking path reported by the tested CS-specific StatsMe build; keep it when moving the server |
| `cstrike/addons/statsme/statsme.log` | Ranking file also supplied by the upstream package; preserve this file too when backing up an existing server |
| `cstrike/addons/yapb/conf/yapb.cfg` | Bot settings and private YaPB password |

Keep credentials private. The repository ignores these local configuration files and generated game data. Configuration can be edited locally after stopping the server; setup is not an updater and does not merge existing configuration.

## Start and connect

Run `Start-Server.cmd` in the package's main folder, or use **Start server** in `Start-Panel.cmd`. The original launcher inside the installed server is `Start-CS15.cmd`. The dedicated server uses UDP port 27015 and LAN mode. Join using HLSW or the client's Multiplayer / LAN Games list. You can also use `connect <server-LAN-address>:27015` in the game console. Allow the game's LAN traffic in the firewall yourself if needed. No Internet port forwarding is needed for LAN play.

Setup writes an explicit `+ip` LAN address into `Start-CS15.cmd`, preferring the network adapter with a gateway and excluding loopback and `169.254.*` link-local addresses. This prevents an additional TAP/VPN adapter from advertising the wrong address. Ambiguous adapter selection requires `Configure-CS15Server.ps1 -BindAddress <assigned-IPv4>`. If DHCP changes the PC's address, update `+ip` in the launcher. Use that same address in HLSW; an explicitly bound server may not answer through `127.0.0.1`.

Configure the exact administrator player name and the private `setinfo _pw` value from `ADMIN.local.txt` before connecting. After connecting, `amxmodmenu` opens the stock AMXX menu. The independent StatsMe password menu is disabled, and no shared public administrator password is installed.

For HLSW administration, select the server, open **Admin > Rcon Konfiguration**, enter the **Server-console RCON password** from `ADMIN.local.txt`, and click **Testen**. **Hole Protokoll (LAN)** enables live log output. Commands in HLSW's console do not need an additional `rcon` prefix.

`ADMIN.local.txt` is a reference sheet, not an active configuration file. Changing its text does not change authentication. Set the actual `rcon_password` in `cstrike/server.cfg` and reload it with `exec server.cfg` from the dedicated console, or restart the server. Then update the reference sheet and HLSW's saved password. The AMXX administrator password is separate from RCON.

### YaPB in-game administration

YaPB 4.4.957 authenticates remote bot commands separately from AMXX. New installations configure the separately chosen YaPB password and the `_ybpw` key. Older installations may still have an empty `yb_password`; AMXX `setinfo _pw` login alone does not grant YaPB access. See the [pinned access implementation](https://github.com/yapb/yapb/blob/4.4.957/src/control.cpp) and [official dedicated-server instructions](https://yapb.github.io/docs/en/configuring/botusage/#bot-management-on-a-dedicated-server).

For a new installation, use the YaPB client command recorded in `ADMIN.local.txt`. For an older server without a bot password, edit `cstrike/addons/yapb/conf/yapb.cfg` to set a unique private password and retain the default key:

```text
yb_password "<your-private-bot-password>"
yb_password_key "_ybpw"
```

Apply the same two commands in the dedicated server console for the current session, or restart after saving the file. Then enter in the game client's console:

```text
setinfo _ybpw "<your-private-bot-password>"
yb menu
```

Replace the placeholder with the same private password on both sides. If access does not update immediately, reconnect and try `yb menu` again. Persist the server settings in `yapb.cfg` so a restart or map change does not restore the empty password. Bot-menu access still needs an in-game acceptance check.

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
