# Additional maps and chat sounds

The `lan-nostalgia-2026-11` pack adds **13 GoldSrc maps and 28 chat sounds**. New installations have 39 maps and 42 chat keywords including the original content. Downloads and selected files are pinned by SHA-256 in [pack.json](../content/pack.json).

## Update an existing server

Stop the server cleanly with `quit`. Keep the entire current repository checkout together, then run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Update-CS15Content.ps1 -ServerDirectory "D:\CS15Server" -WhatIf
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Update-CS15Content.ps1 -ServerDirectory "D:\CS15Server"
```

For the default installation beside `Setup.cmd`, double-click `Update-Content.cmd`. Restart with the server's existing `Start-CS15.cmd`.

The preview makes no changes or downloads. The updater verifies assets before modifying the server, appends new map/sound entries once, and backs up changed files. Conflicting custom maps or keywords stop it before server mutation. Existing shared resources are retained. Credentials, rules, sound quotas/cooldown and ranking are not rewritten. Download cache: `downloads/content`, overridable with `-CacheDirectory`. Updating Git alone does not update a separately installed server.

The result reports a backup directory. To undo the update while the server is stopped:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Restore-CS15Content.ps1 -ServerDirectory "D:\CS15Server" -BackupDirectory "D:\CS15Server\_content\backups\<reported-directory>"
```

Restore checks that affected files have not changed since the update and otherwise stops before mutation. Backups are retained. A new installation completes its base configuration before adding this pack; if a content download fails, retry the updater directly instead of rerunning Setup.

## Maps

Counts come from BSP spawn entities; original maps are not edited. Capacity values are included in Map Manager and legacy mapcycle entries. They guide automatic selection, but do not change the server's 32 slots or prevent an administrator forcing a small map. Map Manager counts human players for eligibility; bot targets must also fit the map.

| Map | CT / T starts | Selection limit |
| --- | --- | --- |
| `de_rats_2001` | 10 / 10 | 20 |
| `awp_map` | 10 / 10 | 20 |
| `fy_iceworld` | 12 / 12 | 24 |
| `fy_pool_day` | 16 / 16 | 32 |
| `fy_snow` | 16 / 16 | 32 |
| `fy_iceworld2k` | 12 / 12 | 24 |
| `aim_ak-colt` | 18 / 18 | 32 |
| `aim_map` | 16 / 16 | 32 |
| `awp_india` | 16 / 16 | 32 |
| `35hp` | 12 / 12 | 24 |
| `he_tennis` | 5 / 5 | 10 |
| `he_glass` | 16 / 16 | 32 |
| `de_rats` | 10 / 10 | 20 |

Use `changelevel de_rats_2001` in the dedicated console for the requested Rats version; use `maps` or `/maps` in player chat for nominations. Twelve maps use official YaPB graphs. Rats 2001 uses a locally generated graph with 546 nodes. All graphs load, but navigation quality on every route requires LAN playtesting.

## New chat sounds

Type a keyword in chat without a slash. Each uses `cstrike/sound/lan/<keyword>.wav`. The original 14 keywords and automatic StatsMe announcements keep their existing configuration.

| Keyword | Seconds | Original source file |
| --- | --- | --- |
| `moin` | 4.66 | `admin_plugin/moin.mp3` |
| `nabend` | 1.53 | `admin_plugin/nabend.mp3` |
| `n8` | 1.18 | `admin_plugin/n8.mp3` |
| `bye` | 3.55 | `admin_plugin/bye.wav` |
| `jaja` | 1.55 | `admin_plugin/jaja.mp3` |
| `sorry` | 0.67 | `admin_plugin/sorry.mp3` |
| `danke` | 0.60 | `admin_plugin/thx.wav` |
| `camper` | 3.35 | `admin_plugin/camper2.wav` |
| `lol` | 1.56 | `admin_plugin/lol.wav` |
| `mimi` | 1.66 | `admin_plugin/mimi.wav` |
| `zielen` | 2.69 | `admin_plugin/zielen.wav` |
| `afk` | 1.29 | `cp/afk.wav` |
| `bier` | 2.36 | `cp/bier3.mp3` |
| `blamage` | 3.08 | `cp/blamage.wav` |
| `bockmist` | 2.71 | `cp/bockmist.wav` |
| `geil` | 1.55 | `cp/geil.wav` |
| `noe` | 1.25 | `cp/noe.wav` |
| `profi` | 2.21 | `cp/profi.wav` |
| `wasndalos` | 1.85 | `cp/wasndalos.wav` |
| `isklar` | 1.75 | `cp/isklar.mp3` |
| `kommgleich` | 1.83 | `cp/kommgleich.wav` |
| `kumpel` | 3.69 | `cp/kumpel.mp3` |
| `wasguckstdu` | 5.79 | `cp/wasguckstdu.mp3` |
| `zonk` | 2.67 | `cp/zonk.mp3` |
| `woohoo` | 0.93 | `agc/woohoo.wav` |
| `beer` | 1.92 | `agc/beer.wav` |
| `comeagain` | 0.89 | `agc/comeagain.wav` |
| `falsch` | 4.06 | `cp/falsch.mp3` |

Open [the offline listening page](../content/Listen.html) to audition the selection. `amx_sound_help` lists keywords in game. Selection used names, duration and local automatic speech recognition; human listening approval remains open. No sound was uploaded for transcription. Original source files were not modified. Long music clips, game-specific effects and exact duplicates were omitted from this initial set. All output is PCM mono WAV, 22050 Hz, 16 bit.

## Extend the pack in Git

For a sound, place a compatible WAV under `content/files/cstrike/sound/lan/`, add its relative source/target and SHA-256 under `localFiles`, then add keyword/path under `sounds` in `content/pack.json`. For a map, add a checksum-pinned ZIP/raw package with explicit member mappings, a map entry with verified capacity, required resources, navigation and author notices. Test on an isolated server before updating a live installation. The updater reads only explicitly listed ZIP members and does not extract archives wholesale.
