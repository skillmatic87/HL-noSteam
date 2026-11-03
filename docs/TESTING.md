# Integration testing

Test date: 2026-11-03. These results describe a developer test installation, not a released package.

## Environment

The original local Half-Life client remains unchanged. A separate HLDS 4.1.1.0 / CS 1.5 installation runs under the short `s` directory in the workspace. It binds to `127.0.0.1:27025`, uses LAN mode and advertises 32 slots with protocol 46. No firewall or router rule was added.

## Observed results

| Check | Result |
| --- | --- |
| Engine startup and legacy UDP status query | Pass: CS 1.5, protocol 46, 32 advertised slots |
| Plugin loader | Four running modules: AMXX, StatsMe, YaPB and FakeMeta |
| AMXX plugin load | 15 running plugins, including stock admin/menu plugins, Map Manager and Sank Sounds |
| Map changes | de_dust and de_dust2 loaded successfully |
| Bots | Two test bots join; game logs record combat, kills and bomb activity |
| StatsMe persistence | Observed: a version-15 ranking file contains a record with four kills after a map change; the server loads a record after a clean process restart. Compatibility blocker below remains open. |
| Automatic map vote | Setting reports 5; log records an automatic start at 298 seconds remaining on a temporary six-minute map, within the plugin's ten-second check interval |
| Sound configuration | Sank Sounds debug output lists all 14 configured keywords and their durations |
| Sound files | All 14 are PCM mono WAVs, using 11025 or 22050 Hz and 8 or 16 bits |
| AMXX runtime errors | No current error log found after replacing the incompatible round event |

Client connection, nomination inclusion, ordinary-player/admin authorization, sound transfer, audible playback to multiple clients, all-map navigation coverage, a second-PC LAN connection and 32-client load remain unverified. A fresh installation from a public release archive is also pending.

The stock map time limit and other upstream settings are used only for development. Temporary six-minute maps exercise vote timing; the two-bot quota and sound limits are test values. They do not resolve the operator choices in [open questions](OPEN-QUESTIONS.md).

## Compatibility findings

- Map Manager 2.5.61 registers the CS 1.6 `HLTV` new-round event, which fails on this CS 1.5 engine. The test preparation script replaces that registration with the existing `World triggered` / `Round_Start` log event and identifies the build as `2.5.61-cs15`. The rest of the vote plugin remains upstream code.
- **Release blocker:** StatsMe 2.8.3 declares `mod_name[32]` and copies the engine's game directory there without a length check. The source also compares that field directly with `cstrike` to select CS-specific behavior. This engine supplies an absolute path and StatsMe logs an empty detected mod. A long initial path produced a truncated ranking path. Persistence was observed at a shorter path, but that path is still 32 bytes and exceeds safe storage including the terminator. The preparation script now rejects paths exceeding 31 bytes; it therefore refuses to rebuild this particular installation. A safe path alone does not repair mod detection. Find a compatible existing StatsMe build or document and test a narrow source correction before release. [Metamod's engine notes](https://metamod-p.sourceforge.net/doc/html/engine_notes.html) describe the pre-1.1.1.1 absolute-path behavior.
- The original AMXX compiler can return exit code zero after a compilation error. Preparation checks its diagnostic text and requires a newly generated output file. Source is written without a UTF-8 BOM because this compiler rejects it.
- A hyphen in the test configuration filename was interpreted incorrectly by the old launch command parser. The working test uses `integration.cfg`.
- The StatsMe retro rank header/body configuration is used because the supplied configuration explicitly identifies it for CS 1.5.

## Developer scripts

`Get-CS15ServerStatus.ps1` sends a read-only legacy GoldSrc status query. For the isolated test server:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Get-CS15ServerStatus.ps1 -Port 27025
```

`Prepare-CS15PluginTest.ps1` is a development helper. It requires the previously extracted baseline server and research downloads, modifies only the disposable `s` installation, builds Map Manager and Sank Sounds, and creates a local disposable RCON credential. Its new path guard intentionally rejects this workspace's current test path until the StatsMe blocker is resolved. It is not an installer for a GitHub download. The path guard and compiler checks have been checked separately; a complete rerun with those additions is blocked by the guard.

`Invoke-CS15TestCommand.ps1` controls only that loopback test server using its ignored local credential file. Raw control logs, saved statistics, credentials, game binaries and research downloads are excluded from Git.
