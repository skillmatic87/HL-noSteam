# v1.0.0 — local control panel and main-folder launchers

Version 1.0.0 packages the Windows installer and the experimental Linux Mint installer as separate source ZIP downloads. First setup downloads and verifies the original server/mod components; it does not include a game client or a preconfigured server with shared credentials.

## Start from the main folder

Windows: run `Setup.cmd`, then `Start-Server.cmd` or `Start-Panel.cmd`.

Linux Mint: install the dependencies in `docs/LINUX-MINT.md`, then run `bash Setup-Linux.sh`, followed by `bash Start-Server.sh` or `bash Start-Panel.sh`.

`START-HERE.txt` provides a short entry guide. Launchers locate their accompanying files relative to the extracted package and support custom server directories. Keep the package together. The panel requires Python 3.10 or newer; direct HTML opening remains a read-only preview.

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

Ranking persistence across map changes/restarts, simultaneous playback with two human clients, a longer gameplay session and 32-client load remain acceptance work. Linux startup/client/admin success is operator-reported; the automated browser/native lifecycle tests ran on Windows. See `docs/TESTING.md` for the distinction between automated and manual results.
