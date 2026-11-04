# Additional maps and chat sounds

The `lan-nostalgia-2026-11` pack adds **13 GoldSrc maps and 108 chat sounds**. New installations have 39 maps and 122 chat keywords including the original content. Downloads and selected files are pinned by SHA-256 in [pack.json](../content/pack.json).

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

## Chat sounds: initial 28

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


## Further 80 operator-selected sounds

All 80 marked files from the operator's desktop review were included on 2026-11-04. Their complete durations were retained. Existing keyword mappings are unchanged; filename collisions use a source-folder suffix. Each clip is PCM signed 16-bit mono WAV at 22050 Hz.

| Chat keyword | Seconds | Original source file |
| --- | ---: | --- |
| `arsch1` | 6.03 | `admin_plugin/arsch1.mp3` |
| `blut` | 3.19 | `admin_plugin/blut.mp3` |
| `burn` | 7.39 | `admin_plugin/burn.mp3` |
| `camperhp` | 4.49 | `admin_plugin/camperhp.mp3` |
| `crazytown` | 73.17 | `admin_plugin/crazytown.mp3` |
| `depp` | 12.88 | `admin_plugin/depp.wav` |
| `dumm` | 1.66 | `admin_plugin/dumm.wav` |
| `eier` | 1.97 | `admin_plugin/eier.wav` |
| `feuerfrei` | 11.39 | `admin_plugin/feuerfrei.mp3` |
| `grr` | 2.40 | `admin_plugin/grr.mp3` |
| `hahaa` | 2.11 | `admin_plugin/hahaa.wav` |
| `hamster` | 9.71 | `admin_plugin/hamster.wav` |
| `hi` | 0.76 | `admin_plugin/hi.mp3` |
| `ja` | 5.54 | `admin_plugin/ja.mp3` |
| `kotzen` | 9.62 | `admin_plugin/kotzen.mp3` |
| `lauf` | 2.72 | `admin_plugin/lauf.wav` |
| `loli` | 3.58 | `admin_plugin/loli.wav` |
| `lucker` | 4.75 | `admin_plugin/lucker.mp3` |
| `mana` | 11.94 | `admin_plugin/mana.mp3` |
| `mojo` | 12.04 | `admin_plugin/mojo.mp3` |
| `mund` | 12.20 | `admin_plugin/mund.mp3` |
| `nice` | 7.27 | `admin_plugin/nice.mp3` |
| `sack` | 7.81 | `admin_plugin/sack.mp3` |
| `wo` | 2.08 | `admin_plugin/wo.wav` |
| `benny` | 14.28 | `agc/benny.mp3` |
| `bitch` | 1.62 | `agc/bitch.mp3` |
| `boogey` | 1.62 | `agc/boogey.wav` |
| `bs` | 1.10 | `agc/bs.mp3` |
| `bull` | 1.67 | `agc/bull.mp3` |
| `bung` | 3.59 | `agc/bung.wav` |
| `camper_agc` | 1.71 | `agc/camper.wav` |
| `comedian` | 2.41 | `agc/comedian.wav` |
| `crap` | 1.22 | `agc/crap.wav` |
| `dipshit` | 1.54 | `agc/dipshit.wav` |
| `fart` | 2.51 | `agc/fart.wav` |
| `gh` | 2.21 | `agc/gh.wav` |
| `haha` | 1.10 | `agc/haha.wav` |
| `imsorry` | 1.67 | `agc/imsorry.wav` |
| `kickass` | 3.80 | `agc/kickass.wav` |
| `muaha` | 3.43 | `agc/muaha.wav` |
| `omg` | 1.36 | `agc/omg.mp3` |
| `ow` | 0.57 | `agc/ow.wav` |
| `stfu` | 1.83 | `agc/stfu.mp3` |
| `stfu10` | 3.24 | `agc/stfu10.mp3` |
| `wazza` | 1.68 | `agc/wazza.wav` |
| `au` | 2.21 | `cp/au.wav` |
| `bekloppt` | 4.70 | `cp/bekloppt.mp3` |
| `benny_cp` | 15.57 | `cp/benny.wav` |
| `biene3` | 6.87 | `cp/biene3.mp3` |
| `blade` | 10.79 | `cp/blade.mp3` |
| `blitz` | 2.60 | `cp/blitz.wav` |
| `chicken` | 8.83 | `cp/chicken.wav` |
| `chicken2` | 9.00 | `cp/chicken2.wav` |
| `chicken3` | 8.93 | `cp/chicken3.wav` |
| `cool` | 1.02 | `cp/cool.wav` |
| `cornholio` | 3.07 | `cp/cornholio.wav` |
| `doh` | 7.31 | `cp/doh.wav` |
| `faithless4` | 17.06 | `cp/faithless4.mp3` |
| `feelgood` | 3.92 | `cp/feelgood.wav` |
| `fuckdup` | 4.84 | `cp/fuckdup.wav` |
| `good-boyyy3` | 2.22 | `cp/good-boyyy3.mp3` |
| `haha_cp` | 7.26 | `cp/haha.wav` |
| `haha2` | 1.69 | `cp/haha2.wav` |
| `hell` | 1.59 | `cp/hell.wav` |
| `jtab` | 67.55 | `cp/jtab.mp3` |
| `kurwa` | 2.43 | `cp/kurwa.mp3` |
| `lala` | 4.08 | `cp/lala.wav` |
| `loser` | 22.53 | `cp/loser.mp3` |
| `mad3` | 3.45 | `cp/mad3.mp3` |
| `otto` | 5.11 | `cp/otto.mp3` |
| `pruegel` | 2.33 | `cp/pruegel.mp3` |
| `runnlauter` | 4.34 | `cp/runnlauter.mp3` |
| `saufen` | 15.34 | `cp/saufen.mp3` |
| `scheisse` | 4.12 | `cp/scheisse.wav` |
| `sonnenschein` | 9.67 | `cp/sonnenschein.mp3` |
| `trains` | 1.21 | `cp/trains.mp3` |
| `vodka` | 12.65 | `cp/vodka.mp3` |
| `welcome` | 1.64 | `cp/welcome.wav` |
| `wow` | 1.01 | `cp/wow.wav` |
| `what_is_that` | 3.85 | `new/what_is_that.wav` |

All 108 additional clips can be auditioned on [the offline listening page](../content/Listen.html). Installed servers have 122 chat keywords with the 14 original defaults. Type the keyword in player chat; `amx_sound_help` lists the commands. Human selection of the 80 originals does not establish audible playback on every CS client.

## Extend the pack in Git

For a sound, place a compatible WAV under `content/files/cstrike/sound/lan/`, add its relative source/target and SHA-256 under `localFiles`, then add keyword/path under `sounds` in `content/pack.json`. For a map, add a checksum-pinned ZIP/raw package with explicit member mappings, a map entry with verified capacity, required resources, navigation and author notices. Test on an isolated server before updating a live installation. The updater reads only explicitly listed ZIP members and does not extract archives wholesale.
