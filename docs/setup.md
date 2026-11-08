# Setup questions

Windows and Linux use the same English questions. Yes/no prompts display `[y/n]`. They accept `y`, `yes`, `j` or `ja` for yes and `n`, `no` or `nein` for no, regardless of case. Empty input repeats the question; it never silently chooses an answer.

| No. | Question | Answer |
| --- | --- | --- |
| 1 | Server name | Text, 1-63 printable ASCII characters |
| 2 | Use a 20-minute map time limit? | Yes: 20. No: enter 6-180 minutes |
| 3 | Enable friendly fire? | Yes/no |
| 4 | Enable bots? | No: disable bots and skip questions 5-6 |
| 5 | Use bots to fill the server up to 16 players? | Yes: 16. No: enter 1-32 players |
| 6 | Use medium bot difficulty? | Yes: medium (2). No: choose 0 novice, 1 easy, 2 medium, 3 hard or 4 expert |
| 7 | Use a 3-second cooldown between chat sounds? | Yes: 3. No: enter 0-300 seconds |
| 8 | Limit each player to 100 chat sounds per map? | Yes: 100. No: enter 1-1000 |
| 9 | Include bots in the ranking? | Yes/no |
| 10 | Rank players by kills minus deaths? | Yes: kills minus deaths. No: kills only |
| 11 | Administrator player name | Exact player name, 1-31 printable ASCII characters |
| 12 | AMX password | Hidden input, followed by Confirm password |
| 13 | YaPB password | Hidden input, followed by Confirm password |
| 14 | RCON password | Hidden input, followed by Confirm password |

Passwords require 1-31 visible ASCII characters. Spaces, quotes, semicolons and backslashes are not supported. Passwords are compared exactly, including case; they are never trimmed or printed. Linux requires a terminal that supports private password entry and refuses an echoed-input fallback.

The ten public choices are saved in `settings.local.json`. Passwords are kept separately in the installed server's actual private configuration files and the private `ADMIN.local.txt` instructions. Do not publish the installed server or its private instructions. YaPB uses its own password and the `_ybpw` client key; AMX uses `_pw`.

Unattended `-SettingsPath` (Windows) or `--settings` (Linux) still accepts the existing ten-field public JSON format. It does not ask questions and generates three separate private passwords. Unknown JSON properties are ignored and are not copied into the saved public settings. JSON is not a password-entry mechanism.

With bots disabled, the saved target is 0 and the inactive difficulty is medium; explicit unattended JSON choices are preserved. Existing configured servers are never reconfigured by setup. Use the local panel's Administration section to change their credentials.
