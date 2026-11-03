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

Client connection, nomination inclusion, ordinary-player/admin authorization, sound transfer, audible playback to multiple clients, navigation quality on every map, a second-PC LAN connection and 32-client load remain unverified. The Windows UI helper failed with `windows sandbox failed: helper_unknown_error: setup refresh had errors`; resetting it and retrying also failed. A command-line launch of an isolated copy of the existing 1.1.0.8 client did not establish a connection. Both client and server test processes were stopped; no client success is claimed.

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

`Get-CS15ServerStatus.ps1` sends a read-only legacy GoldSrc status query. For the isolated test server:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Get-CS15ServerStatus.ps1 -Port 27025
```

`Prepare-CS15PluginTest.ps1` is a development helper requiring the old research layout and baseline `s` directory. It now selects StatsMe 2.7.0. New installations should use `Install-CS15Server.ps1` instead.

`Invoke-CS15TestCommand.ps1` controls only loopback port 27025. With `-ServerDirectory`, it reads the generated local credential from that test installation; otherwise it uses the baseline's disposable credential file. Credentials are not printed. Raw logs, saved statistics, credentials, game binaries and research downloads are excluded from Git.
