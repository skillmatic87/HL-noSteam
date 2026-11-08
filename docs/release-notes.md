# v1.1.1 - Permanent Linux console recording and lowercase package names

- Panel, package starter and migrated installed launchers share one interactive util-linux recorder. Each start gets a unique private `logs/console/cs15-console-<UTC timestamp>-<id>.log`, continuously flushed output and an end marker with exit status when the recorder can finish normally.
- The first panel/package start backs up and enables recording in an existing installed launcher. Game configuration, passwords and the HLDS command are retained. Newly installed launchers already include the recorder.
- Maintained project files and references use lowercase names, including `update.sh`, `start-panel.sh`, `start-server.sh` and `setup-linux.sh`. Installed engine/private filenames retain their compatibility names. The ZIP updater migrates known old package paths with backups and recoverable removals; older updaters need the one-time bootstrap in [updating](updating.md).
- Regression tests cover unique logs, failed starts, signal status and early termination, preserved launch arguments/configuration, launcher backups and idempotent migration. Native Linux PTY/permissions and GNOME window lifecycle remain operator acceptance checks on the Windows development host.

# v1.1.0 - English setup wizard and private password entry

- Windows and Linux now share the fourteen English setup questions in [setup.md](setup.md).
- Confirm 20-minute maps, bot fill to 16 players at medium difficulty, a 3-second chat-sound cooldown and 100 sounds per player per map, or enter custom values after answering no.
- Yes/no answers accept y/yes/j/ja and n/no/nein. Prompts show [y/n]; empty input repeats the question. Disabling bots skips their two follow-up questions.
- Enter and confirm separate AMX, YaPB and RCON passwords without echo. YaPB access is configured with the _ybpw key and included in the private client instructions.
- Credentials stay out of public settings JSON and console output. Unattended ten-field JSON setup remains supported and generates three private passwords.
- Existing server configurations and credentials are preserved; this wizard applies to new installations.

# v1.0.1 — Linux package updater and server fixes

- Fixed server-name validation in Windows setup, Linux setup and the panel: names now support 1-63 printable ASCII characters, independently of the 31-character administrator/player-name limit.
- Overlong setup names report the actual length and the maximum. Existing server settings and credentials are not changed.
- Tested the reported names, a complete 63-character hostname returned by native CS 1.5 HLDS, real browser validation, Windows configuration and Linux input validation.
- `bash update.sh` updates ZIP-extracted Linux packages without Git or reinstallation. It keeps installed game servers and private configuration intact, backs up replaced package files and restores interrupted updates on the next run.
- `version` and the last successfully applied commit ID distinguish package versions from moving branch ZIP downloads. See [update instructions](updating.md) for the one-time download on older packages.
- Linux panel validation uses assigned interface addresses, allowing Mint systems whose hostname resolves only to loopback.
- Panel startup opens an interactive server terminal; Linux requires GNOME Terminal and util-linux `script`.
- New Linux installations normalize the original archive's WAD filenames to lowercase to prevent the recorded `de_prodigy` map-change shutdown. Existing installations retain the separate repair steps in [Linux Mint operation](linux-mint.md).

Updater validation covers offline archive checks, preservation, repeat updates, injected write failures and journal recovery on Windows. Native Mint file locking, permissions and process checks still require operator verification.

# v1.0.0 — local control panel and main-folder launchers

Version 1.0.0 packages the Windows installer and the experimental Linux Mint installer as separate source ZIP downloads. First setup downloads and verifies the original server/mod components; it does not include a game client or a preconfigured server with shared credentials.

## Start from the main folder

Windows: run `setup.cmd`, then `start-server.cmd` or `start-panel.cmd`.

Linux Mint: install the dependencies in `docs/linux-mint.md`, then run `bash setup-linux.sh`, followed by `bash start-server.sh` or `bash start-panel.sh`.

`start-here.txt` provides a short entry guide. Launchers locate their accompanying files relative to the extracted package and support custom server directories. Keep the package together. The panel requires Python 3.10 or newer; direct HTML opening remains a read-only preview.

## Included changes

- Local server start/stop and live status through a loopback-only helper.
- English/German control panel for maps, game rules, bots, sounds, rankings and welcome text.
- Drag-and-drop mapcycle sorting, retained arrow controls and an independent voting selection.
- Administration for AMX player names/passwords, new administrators, RCON and YaPB passwords.
- Reviewed configuration/access saves, verified private backups, undo, stale-file protection and write protection while HLDS is running.
- Existing package content: 39 maps, 122 chat-sound commands, welcome MOTD/join sound and expanded classic-style bot chat.

Existing installations can open the new panel and select their server directory; do not rerun setup over a completed server. Existing passwords are retained unless a replacement is explicitly entered and saved.

## Verification and remaining acceptance

The Windows helper and native server lifecycle, browser settings save/undo, map sorting, access edits and restoration have been exercised using disposable installations. Offline installer and launcher checks cover path handling, incomplete installations and safe configuration inputs. Operator-reported results include LAN joining, administrator access, map changes/votes, sounds, custom-map downloads and bot play.

Ranking persistence across map changes/restarts, simultaneous playback with two human clients, a longer gameplay session and 32-client load remain acceptance work. Linux startup/client/admin success is operator-reported; the automated browser/native lifecycle tests ran on Windows. See `docs/testing.md` for the distinction between automated and manual results.
