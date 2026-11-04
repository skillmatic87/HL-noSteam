# Integration testing

Test date: 2026-11-03. The installer is a preview; human-client acceptance is incomplete.

## Environment

The original local Half-Life client remains unchanged. The isolated baseline uses `s`; a fresh installation uses `runtime/Fresh installation test`, a directory containing spaces and exceeding the rejected StatsMe build's path limit. Tests bind to `127.0.0.1:27025`, use LAN mode and advertise 32 slots with protocol 46. No firewall or router rule was added.

## Observed results

| Check | Result |
| --- | --- |
| Fresh-folder installation | Passed: original server extraction, CS files, plugin compilation, local configuration and launcher generated without files from the existing game installation |
| Public GitHub ZIP | Commit f0c94f7 downloaded, extracted and used to install a second server with verified cached components; it runs 32 slots, four modules, all 15 AMXX plugins and two bots |
| Download integrity | All manifest components verified against their recorded SHA-256 hashes |
| Invalid cache | A deliberately incorrect cached installer is rejected by SHA-256 verification before execution |
| Network/cache paths | Missing graph/README files downloaded over HTTPS and verified; the remaining cache reused; an existing installation is refused before modification |
| Setup input regression | Ten checks cover explicit yes/y/no/n choices, empty/invalid answers, name validation, numeric ranges/overflow and ranking spelling |
| Configuration interruption/retry | Prepared files retained when input ends; configuration resumes without reinstalling; empty/invalid inputs repeat the same question |
| License file | Original SERVER-LICENSE.txt retained; no interactive license prompt |
| Retry protection | Completed installations and pre-license directories containing unrelated files are refused without changing those files |
| Engine startup and legacy UDP status query | Pass: CS 1.5, protocol 46, 32 advertised slots |
| Plugin loader | Four running modules: AMXX 1.8.1.3746, StatsMe 2.7.0, YaPB 4.4.957 and FakeMeta |
| AMXX plugin load | 15 running plugins, including stock admin/menu plugins, Map Manager and Sank Sounds |
| Map changes | de_dust, de_dust2, as_tundra and de_vegas loaded successfully |
| Bots | Two test bots join; game logs record combat, kills and bomb activity |
| StatsMe detail | One recorded entry contains a kill, 127 damage, seven shots and four hits |
| StatsMe persistence | Three version-9 ranking records remain byte-for-byte identical after a clean restart with bots disabled; only the header timestamp changed |
| Bot graph files | 24 supplied by YaPB; official graphs added for as_tundra and de_vegas, both running with two bots |
| Automatic map vote | Setting reports 5; log records an automatic start at 298 seconds remaining on a temporary six-minute map, within the plugin's ten-second check interval |
| Sound configuration | Sank Sounds debug output lists all 14 configured keywords and their durations |
| Sound files | All 14 are PCM mono WAVs, using 11025 or 22050 Hz and 8 or 16 bits |
| AMXX runtime errors | No current error log found after replacing the incompatible round event |

At this initial test stage, client connection, nomination inclusion, ordinary-player/admin authorization, sound transfer, audible playback to multiple clients, navigation quality on every map, a second-PC LAN connection and 32-client load were unverified. The Windows UI helper failed with `windows sandbox failed: helper_unknown_error: setup refresh had errors`; resetting it and retrying also failed. A command-line launch of an isolated copy of the existing 1.1.0.8 client did not establish a connection. Both initial test processes were stopped. Later client results are recorded below.

The stock map time limit and other upstream settings are used only for development. Temporary six-minute maps exercise vote timing; the two-bot quota and sound limits are test values. They do not resolve the operator choices in [open questions](OPEN-QUESTIONS.md).

## Compatibility findings

- Map Manager 2.5.61 registers the CS 1.6 `HLTV` new-round event, which fails on this CS 1.5 engine. The test preparation script replaces that registration with the existing `World triggered` / `Round_Start` log event and identifies the build as `2.5.61-cs15`. The rest of the vote plugin remains upstream code.
- **Rejected candidate:** StatsMe 2.8.3 copies the engine's absolute game directory into `mod_name[32]` and compares it directly with `cstrike`. This caused unsafe path handling and incomplete CS detection. [Metamod's engine notes](https://metamod-p.sourceforge.net/doc/html/engine_notes.html) document the old engine's absolute-path behavior.
- **Selected original build:** The unmodified CS-specific StatsMe 2.7.0 binary sets the mod name to `cstrike` and selects CS behavior at compile time. It records damage and hit statistics, works in the long fresh-installation path and saves version-9 ranking files. The rejected candidate's version-15 test records are stored separately and are not migrated automatically.
- StatsMe 2.7 resets its in-memory last-reset timestamp at startup when loading records. Whole-file hashes therefore change; comparing the record bytes confirms persistence. Automatic rank resets are disabled by setup.
- The original AMXX compiler can return exit code zero after a compilation error. Preparation checks its diagnostic text and requires a newly generated output file. Source is written without a UTF-8 BOM because this compiler rejects it.
- A hyphen in the test configuration filename was interpreted incorrectly by the old launch command parser. The working test uses `integration.cfg`.
- The StatsMe retro rank header/body configuration is used because the supplied configuration explicitly identifies it for CS 1.5.

## Developer scripts

### Client, LAN and operator checks (2026-11-03)

| Check | Observed result |
| --- | --- |
| CS 1.5 client | Half-Life WON 1.1.1.0 / protocol 46 client connection accepted through the internal IPv4 address |
| HLSW joining | Launched the installed client with `-game cstrike`; server accepted the connection and administrator password |
| RCON password change | Operator-selected password activated and persisted; authenticated `status` succeeded without a server restart |
| Server adapter selection | Explicit Ethernet `+ip` replaces an incorrectly advertised TAP link-local address; server status and query response report the intended LAN address |
| LAN selection regression | Gateway selection, TAP/link-local exclusion, isolated LAN without a gateway, explicit address validation and ambiguous-adapter rejection pass |
| Game menu server entry | Direct LAN address added through Play Online / Add IP; server row visibly shows map and player count; favourite persisted to `favsvrs.dat` |
| Automatic LAN browser | Still empty on the test PC with a preferred TAP adapter; no routing or firewall changes applied; direct saved entry works around discovery |
| Display mode inventory | Full HD and QHD available on the primary display; unsupported 4K profile rejected before registry mutation |
| Video settings preservation | Repeated profile changes preserve unrelated credential and audio sentinel values |
| Desktop launchers | Direct shortcuts select Half-Life with `-game valve` and Counter-Strike with `-game cstrike`; target, arguments and working directory verified |

Visual Full HD/QHD gameplay, FOV, audible sound playback to multiple clients, second-PC discovery/connection and 32-client load remain open. Desktop shortcuts, installed game binaries, operator addresses, credentials and raw evidence remain local. See [client setup](CLIENT.md).

### Additional content pack

Sound expansion on 2026-11-04:

| Check | Observed result |
| --- | --- |
| Operator selection | All 80 marked source files matched the reviewed desktop list and saved source checksums |
| Conversion | All 80 outputs are nonempty PCM signed 16-bit mono WAV at 22050 Hz; duration differs from the source inventory by less than 0.3 seconds; no clip was intentionally trimmed |
| Keyword collisions | New `camper_agc`, `benny_cp` and `haha_cp` mappings preserve existing commands |
| Content regression | Preview, conflict/corruption rejection, protected configuration/ranking/text, repeat update and exact rollback pass with 108 additional sounds |
| Installed server | Updated with a content backup, restarted on the same map, 15 plugins running, all 122 keywords and all 122 nonzero sound durations reported by Sank Sounds |
| Operator data | Eight existing protected launcher/configuration/ranking files retained identical bytes across the stopped-server update; sound quota 100 and delay 3 seconds retained |
| Local client | All 80 new WAVs preloaded and checksum-verified in the installed game client |

The additional pack now contains 108 sounds, with 122 total keywords including the original 14. Audible playback on multiple CS clients remains a separate acceptance check. The initial 28-clip evidence below is historical.

The `lan-nostalgia-2026-11` pack was implemented and tested on 2026-11-03:

| Check | Observed result |
| --- | --- |
| Map archives | All 13 pinned ZIPs downloaded and inspected; each map is GoldSrc BSP version 30 |
| Spawn counts | Recorded per team; Map Manager and mapcycle entries contain limits from 10 to 32 players |
| Engine map loading | All 13 maps loaded on the CS 1.5 protocol-46 test server: de_rats_2001, awp_map, fy_iceworld, fy_pool_day, fy_snow, fy_iceworld2k, aim_ak-colt, aim_map, awp_india, 35hp, he_tennis, he_glass and de_rats |
| Navigation loading | All 13 maps reported a loaded nonempty YaPB graph; Rats 2001 auto-analysis generated 546 nodes and added bots |
| Sound processing | 28 selected local clips converted to PCM signed 16-bit mono WAV at 22050 Hz; original files unchanged |
| Runtime sound parsing | Sank Sounds lists all 42 keywords, including the original 14, with nonzero durations |
| Fresh installation | Complete base install plus content pack succeeded in a new directory containing spaces; 39 BSP files, 42 loaded keywords, 15 running plugins and the bundled 546-node Rats graph verified after startup |
| Setup regression | All ten input cases and full interrupted-configuration/resume test passed with additional content enabled |
| Updater preview | No server files or downloads created by the preview |
| Corrupt/conflicting content | A deliberately wrong SHA-256 and an unrelated existing AWP map were rejected before server mutation |
| Local data preservation | Fixture checks preserve credentials, both ranking-file locations, unrelated shared resources, sound quota/cooldown, Unicode comments and original text bytes |
| Repeated update | No changed files or duplicate map/keyword entries |
| Rollback | Exact original fixture state restored; a subsequent operator edit first prevented restore before mutation |
| Installed operator server | Updated and restarted using its existing launcher on port 27015; protocol 46, 32 slots, 39 map files, 42 sound keywords, 15 running plugins, original sound quota 100 and delay 3 seconds verified |

The installed-server update retained checksums for the seven existing protected configuration/launcher files it checked. Ranking files are outside the updater's change set. Raw evidence and the live backup location are retained locally under `runtime/content-work`; private hashes and logs are not published.

Map loading and graph availability do not establish every route's navigation quality or 32-client suitability. Stock Half-Life skies are supplied by a compatible client's original game assets. Client downloads, visible map resources, audible playback and human approval of the sound selection remain to be checked in actual LAN play. Selection used local automatic transcription, which can misidentify short clips; [the offline preview](../content/Listen.html) allows human audition.

Run content mutation/protection regression checks with:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Test-CS15Content.ps1 -CacheDirectory .\downloads\content
```

Fixtures are retained under ignored `runtime` directories for inspection. `New-CS15SoundPreview.ps1` regenerates the listening page from the manifest. See [content operation and rollback](CONTENT.md).

`Test-CS15SetupInput.ps1` checks console input with simulated answers. Passing `-IntegrationCacheDirectory` also runs a fresh installation, interrupts it before settings are written, checks protection of operator edits, and completes the interactive configuration through empty/invalid inputs. It verifies that resuming does not extract the server again. Test settings remain separate from operator choices.

`Get-CS15ServerStatus.ps1` sends a read-only legacy GoldSrc status query. For the isolated test server:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Get-CS15ServerStatus.ps1 -Port 27025
```

`Prepare-CS15PluginTest.ps1` is a development helper requiring the old research layout and baseline `s` directory. It now selects StatsMe 2.7.0. New installations should use `Install-CS15Server.ps1` instead.

`Invoke-CS15TestCommand.ps1` uses loopback port 27025 by default; `-ServerAddress` and `-Port` select an explicitly bound local server. It refuses addresses not assigned to this PC. With `-ServerDirectory`, it reads the quoted local credential from that installation, including operator-selected ASCII passwords; otherwise it uses the baseline's disposable credential file. Credentials are not printed. Raw logs, saved statistics, credentials, game binaries and research downloads are excluded from Git.
