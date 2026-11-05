# Local server panel

Run **Start-Panel.cmd** on Windows or **bash Start-Panel.sh** on the Linux branch. Both starters are in the package's main folder beside setup and **Start-Server.cmd / Start-Server.sh**. The local helper opens the browser panel in the background on Windows. Python 3.10+ is required; no third-party packages or Internet connection are needed. The helper listens only on `127.0.0.1` and controls HLDS on that same computer. The HTML document is `Configure-Server.html`; its interface is called the **Server Control Panel**.

English is the default UI language. Choose **English** or **Deutsch** using the language selector at the top right. The choice is stored in the browser for that panel address. Switching languages retains pending edits and does not translate server names, map names, sound commands, MOTD contents or configuration values. Labels, validation, status messages, review dialogs and helper errors follow the selected language. All translations are embedded in the HTML file and work offline.

## Use

1. Open the starter or desktop panel shortcut. Choose **Open server folder** and select the installed root with `cstrike` and its `Start-CS15.cmd` or `Start-CS15.sh`. A `CS15Server` folder beside the checkout is detected automatically.
2. Change maps/votes, duration, slots, start map, game limits, bots, sounds, ranking or MOTD.
3. Use **Stop server** before saving. The helper sends regular RCON `quit` using the private password already in `cstrike/server.cfg`. It does not force-kill an unresponsive server.
4. Choose **Review changes**, review files and before/after values, then **Save with backup**.
5. Use **Start server**. The panel shows startup/running/stopped state, current map and player counts. Save pending settings before starting.

Closing the page does not stop HLDS. Reopening the Windows starter reuses the helper. Legacy Windows HLDS uses a separate hidden console because it needs real console input handles. Only the generated launcher arguments are supported; arbitrary shell/batch setup routines are not executed.

For a specific Windows folder, run `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Start-CS15Panel.ps1 -ServerDirectory "D:\CS15Server"`. On Linux, run `python3 scripts/server_panel.py --server /path/to/CS15Server-Linux --open-browser` on the server computer. The optional native folder chooser needs Python Tk; otherwise enter the path. Native Linux process control has not yet been accepted on Linux.

## Map order and administration

In **Maps & Rotation**, drag a rotation map by its **⠿** handle onto the upper or lower half of another rotation row to insert it before or after that map. The search filter retains hidden entries in the full cycle. The **↑ / ↓** buttons also work with a keyboard. Save the resulting mapcycle using **Review changes**. Reordering the rotation does not reorder or change the independent voting selection.

Open **Administration** to edit existing name-based AMX administrators, add another full administrator, or change RCON and YaPB passwords. Existing AMX permission flags are retained; Steam/WON-ID, IP and clan rules remain untouched. Setting a new AMX password enables password checking if that account previously bypassed it. Login commands show the configured AMX and YaPB userinfo keys.

Password inputs start empty: leave them blank to keep the current value. New accounts require a password. Names and new passwords accept 1–31 basic ASCII characters; passwords cannot contain spaces. Quotes, semicolons and backslashes are rejected. Current passwords are not sent to these form fields or displayed in the review. Administrator names and access drafts are excluded from exported settings profiles.

Stop HLDS, choose **Review access changes**, then **Save access with backup**. Restart the server and reconnect with the updated player name and client `setinfo` value. Update the RCON password saved in HLSW as well. Game settings retain their own save/review button. A successful access save preserves pending game edits and reloads changed configuration snapshots so the next settings save retains the new credentials.

Access saves create a private `_configurator/backups/<timestamp>-access-<id>/` backup and a checked `admin-restore.json`. **Undo last access save** restores it within the current page session. Restoration is blocked if affected files changed subsequently. A successful access save clears the ordinary settings undo action to avoid restoring obsolete credentials. Backups remain on disk when the page closes. `settings.local.json` and the primary operator instructions in `ADMIN.local.txt` are synchronized when applicable.

## Browser restrictions

Chromium on Windows may reject direct File System Access calls for protected extensions such as `.cfg` and `.ini` with `Name is not allowed`. Folder permission alone is insufficient. The helper uses normal application file I/O without changing browser protections.

Opening `Configure-Server.html` directly supports examples, read-only folder import and portable profiles. Saving and Start/Stop require the starter. The page requests only its own loopback helper; GitHub links navigate externally only when clicked.

### Linux: helper rejects the local server address

If **Helper unavailable** appears together with **Die Startdatei verweist nicht auf eine IPv4-Adresse dieses PCs.**, the helper is responding but its old address validation may be rejecting the assigned LAN IP. Mint can resolve its hostname only to `127.0.1.1`; this does not enumerate the addresses on its network interfaces.

The Linux helper now reads assigned IPv4 addresses using `ip -j -4 address show`, provided by the existing `iproute2` dependency. Multiple interfaces and secondary addresses are included. Nonlocal, broadcast and multicast targets remain rejected. The panel itself still listens only on `127.0.0.1` and requires its local Host/Origin and session token. Windows keeps its existing hostname-based check for non-loopback addresses.

For an existing Linux package, replace `scripts/server_panel.py` with the updated Linux-branch copy, stop the old panel helper with Ctrl+C in its terminal, then run `bash Start-Panel.sh` again. Use the newly opened local browser address and keep the helper terminal open. The installed game server, its private settings and its LAN address do not need to be replaced. If `iproute2` is unavailable or its output cannot be read, the helper reports an explicit lookup error instead of accepting an unverified address.

## Files and backups

Only changed settings are written. The regular settings save preserves credentials, launcher address/port arguments and unrelated config lines. The dedicated Administration save can update `users.ini` and selected credential fields after a separate review; it preserves unrelated account rules. Ranking databases, binaries, graphs and WAV files are not written. Bot controls do not replace chat text. Rotation and nomination/vote availability are independent; existing map limits are retained. New entries use package capacity values where known.

Disabled sound commands use the `# CS15CFG-OFF` comment prefix. Simple WAV mappings can be enabled/disabled and previewed; custom directives remain intact. Profiles contain editable choices, map lists and sound flags without raw config or credentials. Imports validate maps and retain current sound mappings. Existing `settings.local.json` choices are synchronized when changed.

Current bytes are checked against loaded snapshots before writing. Original files, `restore.json` and a restore note are verified in `_configurator/backups/<timestamp>/` before changes. Completed temporary copies replace files while retaining permissions. Failed saves roll back already-written files if still unchanged externally; conflicts are reported for manual recovery.

**Undo last save** restores the latest save in that browser session after checking for subsequent edits. Older backups can be restored manually with HLDS stopped. Keep backups private: backed-up `server.cfg` includes its RCON password. UTF-8/BOM and legacy single-byte files are supported. New MOTD text is limited to 1,500 basic characters and previewed as plain text.

Writes are blocked while HLDS runs. A save/undo reservation also prevents another panel tab from starting the game or switching folders during the operation; abandoned reservations expire after two minutes.

## Local access and testing

Requests require a session token and matching local origin/Host. Traversal and linked paths are rejected. Only managed config/launcher files and their backups can be changed; allowed WAVs can be read for previews. Windows metadata and diagnostics stay in `%LOCALAPPDATA%\CS15ServerPanel`.

Run `python scripts/test_server_panel.py` for regression tests covering config extensions, local access, path restrictions, atomic writes, stale selections, running-server protection, edit reservations, localized folder titles and exact RCON quit requests. Access tests additionally cover sanitized metadata, name-only edits, new accounts, preserved rights and special rules, credential validation, revision conflicts, exact private backups, restore conflicts, corrupted backups and rollback after an interrupted write.

Browser language checks cover the English default, both languages' labels/attributes/dynamic tables, persisted choice, unsaved edit preservation, unchanged MOTD contents, review pluralization, validation and confirmation messages, real helper error translation and the narrow-screen selector. Language changes on the loaded operator server produced no configuration changes.

The complete flow was tested in real Chrome against the real loopback helper, without substituted filesystem handles. A disposable Windows HLDS started on isolated UDP 27036, answered GoldSrc queries, rejected writes while running and stopped through RCON quit. A ten-file save, byte-exact backups, undo and external-edit protection passed. The installed operator server was not started or reconfigured by those tests.

The map/admin extension was also tested with real Chrome and the HTTP helper against disposable files: actual drag/drop, filtered lists, arrow sorting, cycle save/reload, separate voting, AMX rename/new accounts, RCON/YaPB replacement, blank-password preservation, private backup/undo, retained pending game edits, a later settings save preserving credentials, revision-conflict rejection, profile/review exclusion of secrets, both languages and narrow-screen layout. Operator credentials were not changed.
