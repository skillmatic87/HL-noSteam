# Open questions

Unanswered questions remain open. Proposed values are not treated as approved requirements.

## Confirmed requirements

- Public repository: `skillmatic87/HL-noSteam`.
- The entire project repository and its deliverable must use English.
- Deliver a working server configuration that is easy to install from GitHub, preferably by extracting and copying files.
- First target: CS 1.5 dedicated server, Windows, LAN, 32 player slots.
- Perform the first tests on the development PC.
- Include existing mods: StatsMe, map voting, nominations, chat sounds, bots and an admin menu.
- Start the map vote five minutes before the map ends.
- Only administrators may use the admin menu.
- All players should hear chat-triggered sounds. Research and download an existing classic sound pack.
- "Global ranking" means persistent statistics stored on this server; a cross-server service or website is not required.
- Include the server itself if the applicable distribution terms permit this.
- Sank Sounds has been accepted as the chat-sound plugin candidate.

## Awaiting operator choices

- Map time limit and Friendly Fire setting.
- Bot population, difficulty and whether bots should leave as humans join.
- Original CS 1.5 maps first, or additional custom maps?
- Sound cooldowns, per-player quotas and who may trigger sounds.
- Whether bots should contribute to the ranking.
- Ranking formula, reset policy and LAN player identification.
- Administrator identities and permissions. Do not post passwords in the public repository or chat.
- Minimum supported Windows version and optional automatic startup.

A proposal has been submitted but is not yet approved: 30-minute maps, Friendly Fire off, bots filling to 16 total players at medium difficulty, while retaining 32 server slots.

## Questions to resolve through inspection and testing

- Which Windows HLDS package and accompanying distribution terms can be used?
- Can a fresh downloadable package reproduce the tested combination without research files already present?
- Do client tests confirm Map Manager nominations, Sank Sounds playback and administrator permissions?
- Are all component distribution notices and corresponding source requirements covered by the final package?
- Does the bot package have navigation data for each included map?
- Does name-based LAN ranking meet the operator's needs when human players change or share names?

The current installer uses HLDS 4.1.1.0, AMXX 1.8.1, the original CS-specific StatsMe 2.7.0, Map Manager 2.5.61 with a CS 1.5 round-event adaptation, Sank Sounds 1.9.1, the 14-file StatsMe sound pack and YaPB 4.4.957. A fresh server installation, automatic voting and preserved ranking records have been observed; see [test results](TESTING.md). The setup wizard asks for operator choices rather than treating an unanswered proposal as approved.

Half-Life Deathmatch remains part of the broader research. The first agreed deliverable is the CS 1.5 LAN package.
