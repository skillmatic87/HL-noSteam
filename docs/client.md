# Local CS 1.5 client: widescreen and LAN

These helpers target a separately installed Half-Life WON 1.1.1.0 client with Counter-Strike 1.5. Server setup does not install a client, game license or widescreen binaries.

## Desktop shortcuts

Create two desktop shortcuts pointing directly to your installed `hl.exe`. **Half-Life** uses `-game valve -console -gl -32bpp -noextracds`, and **Counter-Strike 1.5** uses `-game cstrike -console -gl -32bpp -noextracds`. Set each shortcut's working directory to the game directory. In Half-Life, open **Custom Game**, select **Counter-Strike**, then choose **Activate** to switch mods. Both shortcuts use the saved video resolution and do not connect to a server automatically. No CMD launcher is required.

## Display profiles

The tested client uses UCyborg's WON resolution/FOV patch v1.1 (`hl.exe` for Half-Life 1.1.1.0 and `hl_fov_fix.asi`). These binaries are not included in Git. Back up your original executable before installing the matching patch. OpenGL and 32-bit colour are selected by the optional profile helper. Keep the normal CS FOV setting: the ASI adjusts it for the aspect ratio.

| Helper profile | Requested game resolution |
| --- | --- |
| `Auto` | Current primary desktop resolution |
| `FHD` | 1920 x 1080 |
| `QHD` | 2560 x 1440 |
| `4K` | 3840 x 2160, only when Windows exposes this mode |
| `Safe` | 1024 x 768 |

Quit the game before changing profiles. The maintained helper is `scripts/start-cs15client.ps1`. It expects the client executable and patch in the repository root; for another installation, use its normal desktop shortcut and video menu instead.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start-cs15client.ps1 -ListModes
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start-cs15client.ps1 -Resolution QHD
```

The helper checks Windows display modes before changing settings. It updates individual video values under the existing user registry key and preserves other values. It does not change the monitor or graphics driver configuration. The current PC exposes Full HD and QHD, but no 4K mode. The old menu may retain its own small resolution; menu size is separate from game resolution.

## LAN connection

Join through HLSW or the game's **Play CS > Play On LAN** menu. No dedicated join launcher is required.

If the automatic LAN list stays empty, use **Play CS > Play Online > Add IP**, enter the server's internal address and port, then select the saved entry and **Join Game**. The asterisk marks the favourite. Despite the menu's name, an entry such as `192.168.1.10:27015` connects to the local LAN address. The old WON server lookup may time out before the list opens. The favourite remains saved in `favsvrs.dat` after closing the list.

On the test PC with an additional TAP adapter, diagnostics confirmed that `info`, `details` and `infostring` queries reach the server via Ethernet broadcasts. An unbound limited-broadcast query got no response. Client startup `+ip` and a separate local host port did not make the old menu's LAN list populate. A saved direct entry was visibly verified instead. No Windows routing, VPN, firewall or interface settings were changed.

In HLSW, set the **Half-Life (WON)** game path to your game directory and select `hl.exe`. Add `-game cstrike -console -gl -32bpp -noextracds` to launch CS directly. Use the saved video resolution or configure optional resolution parameters in HLSW.

Use the server PC's internal IPv4 address, not its public Internet address. Other players need an address in the server's LAN subnet. Setup writes an explicit `+ip` into the server launcher to prevent an additional adapter from advertising the wrong address. Update it and saved server entries if DHCP changes the address.

The server retains `sv_lan 1`. Valve documents the same-router/internal-IP case for the “LAN servers are restricted to local clients (class C)” error in its [LAN troubleshooting article](https://help.steampowered.com/en/faqs/view/58CB-73CB-1709-6182). Do not change LAN mode just to work around an incorrect server address.

For automatic administrator login, add `exec csadmin.cfg` to the client's `cstrike/autoexec.cfg` and place your own `setinfo _pw` line from the installed server's `ADMIN.local.txt` in `cstrike/csadmin.cfg`. Use a simple filename: the tested old engine rejected a multi-dot configuration filename. Keep this optional credential file private; it is excluded from Git.

## Validation and local backup

Verified on 2026-11-03: available Windows modes, preservation of unrelated registry values across repeated profile changes, rejection of unsupported 4K before settings change, explicit Ethernet server binding, an accepted HLSW connection with administrator authentication, and a visible direct server entry in the game menu. The user entered the CD key directly in the game. Automatic LAN discovery, visual Full HD/QHD gameplay, FOV and audible playback remain unaccepted.

The video helper uses `RegistryKey.CreateSubKey` and updates individual values. Never replace the whole Half-Life Settings key with the registry provider's `New-Item -Force`, which can erase unrelated preferences and the saved license key. `scripts/test-cs15clientsettings.ps1` verifies that unrelated credential and audio sentinel values survive repeated changes. Enter your own original game key directly in the game if asked. Preserve your original executable, configuration and video settings before applying third-party patches.

Patch sources: [author documentation](https://www.moddb.com/games/half-life/downloads/half-life-won-resolution-fov-mp3-patch), [v1.1 download mirror](https://www.gamepressure.com/download/half-life-half-life-won-resolution-fov-mp3-patch-v11-mod/z91121d), [author's matching FOV component](https://github.com/UCyborg/hl-fov-fix/releases/tag/v1.0). Local research records file hashes and the difference between v1.1 and the newer v1.1.2.
