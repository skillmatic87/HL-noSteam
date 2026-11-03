# Sources and compatibility notes

Research date: 2026-11-03. Downloaded, inspected, installed and runtime-tested are separate states.

## Game and server

| Source | Use | Verification limit |
| --- | --- | --- |
| Local `hl.exe` and bundled `readme.txt` | Initial Half-Life version: 1.1.0.8 | No runtime build established |
| [Valve anniversary update](https://www.half-life.com/en/halflife/25th) | Steam branch and `steam_legacy` | Separate from retail patches |
| [Valve announcements](https://steamcommunity.com/app/70/announcements/) | Official update notes | No live Steam depot build queried |
| [CS archive](https://github.com/Ch0wW/counterstrike-betas) and [CS 1.5 README](https://github.com/Ch0wW/counterstrike-betas/blob/cs15_retail/README.md) | CS 1.5 files and recommended engine versions | Preservation archive; local integration untested |
| [Windows HLDS archive](https://archive.org/details/goldsrc_hlds_won_windows) and [second listing](https://archive.org/details/hlds_20250228) | Original `hlserver4110.exe` | Size and MD5 match; included license inspected |
| [HLDS at ModDB](https://www.moddb.com/downloads/half-life-dedicated-server-4110) | Additional size and MD5 listing | Community upload |
| [WON2 server project](https://github.com/Ch0wW/docker-hlds-won2) | Protocol and plugin research | Linux; not the Windows deployment |
| [Historical server guide](https://v5.steamlessproject.nl/index.php?page=stepbystepserver) | Standalone installation sequence | Some links no longer work |

## Existing mods

| Component | Source | Current state |
| --- | --- | --- |
| StatsMe 2.8.3 | [Original files](https://sourceforge.net/projects/statsme/files/StatsMe/v2.8.3/) | Binary, configuration, GPL text and source downloaded |
| ClanMod 1.82b1 | [Original files](https://sourceforge.net/projects/clanmod/files/ClanMod/ClanMod%201.82b1/) | Downloaded admin-menu candidate |
| AMX Mod X 1.8.1 | [Original base package](https://sourceforge.net/projects/amxmodx/files/AMX%20Mod%20X%20Base/1.8.1/) | Downloaded; SHA-256 matches project page |
| AMXX compatibility | [Official 1.8.2 notes](https://wiki.alliedmods.net/Amx_mod_x_1.8.2_release_notes) | Historical engine/module compatibility needs testing |
| Metamod-P | [Official releases](https://github.com/Bots-United/metamod-p/releases) | Windows v1.21p109 downloaded |
| DeagsMapManager 3.23 | [Preserved files](https://github.com/ty-porter/deagsmapmanager) | Source and compiled plugin downloaded |
| Sank Sounds | [Author's source](https://github.com/ZTHawk/HL1_SankSounds) and [original discussion](https://forums.alliedmods.net/archive/index.php/t-5055.html) | Source downloaded; sound archive retrieval incomplete |
| YaPB | [Releases](https://github.com/yapb/yapb/releases) and [supported engines](https://yapb.github.io/docs/en/getting-started/introduction/) | Windows 4.4.957 downloaded; documentation lists WON support; actual integration untested |

## Inspection tooling

[WiseUnpacker](https://github.com/mnadareski/WiseUnpacker) extracted the original Wise-based HLDS installer without running its setup. This research tool is not automatically a final server dependency.

## Recorded downloads

| File | SHA-256 |
| --- | --- |
| `hlserver4110.exe` | `178fdf8a3d43ab91063ccb83be05be0457c98db348fc28eba6b9c9ea4e5dc849` |
| `counterstrike-cs15_retail.zip` | `5866d247cebe3356f93119310d85b59af5c20f556fb9d5dc891c5563f4a36434` |
| `statsme-2.8.3-cstrike.zip` | `b6ce9d69df97972c60e78bdf323eef9626e8b59fc51188d8df99993dbaf8dca1` |
| `ClanMod1.82b1.zip` | `018f9695947337178577dcb69f6bd68e387ae1a14a92aff74f5b1211bbc4d973` |
| `amxmodx-1.8.1-base.zip` | `8d5d07361f3479e38f2392d209fad7032f755b57aa70c38c0310f98313a610c3` |
| `yapb-4.4.957-windows.zip` | `c32a5b4d77c08c3c59c417568c5719f9227238c6d627d478cfb1d9f7d9c113f4` |
| `metamod-p-v1.21p109-win32.tar.xz` | `564838d9a42032ee3bc44eeb2616896e0789c3ce8d7a033d81f3f795b67e31ed` |

Local hashes identify inspected files. Independent matching references are recorded only where checked; a computed hash alone does not prove authenticity. HTML returned by failed downloads is excluded from candidate packages.
