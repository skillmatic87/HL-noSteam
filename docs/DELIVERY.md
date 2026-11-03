# Delivery requirements and acceptance checks

## Agreed first release

Build an English-language Windows package for a **Counter-Strike 1.5 dedicated LAN server with 32 player slots**. Users should be able to download it from GitHub and install it with a short extraction/copying procedure.

Use existing server mods. Required features are StatsMe, a ranking saved on this server, map nominations, a map vote five minutes before the map ends, maps, bots, an administrator-only menu, and chat sounds audible to all players. Sank Sounds has been accepted as the chat-sound plugin candidate.

The preview currently supplies setup scripts that download verified original components, then assemble a new installation locally. A fully offline distribution and full client acceptance are still pending. The original HLDS installer and its license are preserved by setup.

## Intended user flow

1. Download a versioned package from GitHub.
2. Extract it and follow the short English instructions.
3. Copy the files into the documented location, or use the documented setup step if original installers must be preserved separately.
4. Configure the administrator account locally.
5. Start the dedicated server with the included launcher.
6. Connect using a compatible CS 1.5 client on the LAN.

The package must state which original files it includes and which prerequisites the user must provide. Administrator credentials must be configured locally rather than shipped as a shared public password.

## Acceptance checks

- Install from a freshly extracted download into a new test directory without hidden dependencies on the developer's game folder.
- Verify actual client, engine and plugin versions.
- Start a dedicated CS 1.5 server in LAN mode with 32 configured slots.
- Verify client connection, map loading, map changes and restart.
- Verify StatsMe records known test actions and retains rankings across map changes and restarts.
- Verify nominations reach the vote and the automatic vote starts at the required five-minute mark.
- Verify a normal player cannot use the admin menu or its privileged commands; verify an authenticated administrator can.
- Verify bots join and play using appropriate navigation data.
- Verify required sounds reach a connecting client and chat triggers play to all intended listeners.
- Check plugins for loading failures and runtime errors.
- Match the installation instructions, package contents and recorded test evidence.
- Report missing prerequisites clearly and avoid silently overwriting operator settings.
- Exclude credentials, real player logs and saved operator statistics from the public download.

Configuring 32 slots does not demonstrate a load test with 32 connected clients. A second-machine LAN connection and simultaneous sound playback on multiple clients must also be reported separately from tests performed only on the development PC.

## Unresolved settings

See [open questions](OPEN-QUESTIONS.md). Map rules, bot population, sound limits and detailed ranking policy have not all been approved.
