# Update a Linux ZIP installation

Stop the game server, close the browser panel, then stop its helper with **Ctrl+C in the terminal that runs `Start-Panel.sh`**. Open a terminal in the extracted **package folder**, beside `Setup-Linux.sh`, and run:

```bash
bash Update.sh
bash Start-Panel.sh
```

Do not run the updater with `sudo`. It requires Python 3.10 or newer and an Internet connection; Git is not needed. Folder names containing spaces are supported.

## Add the updater to an older ZIP installation

Older packages do not contain `Update.sh`. Open a terminal in the existing package folder and run this once:

```bash
python3 -c 'import pathlib, urllib.request; p = pathlib.Path("Update.sh.download"); urllib.request.urlretrieve("https://raw.githubusercontent.com/skillmatic87/HL-noSteam/linux-mint-server/Update.sh", p); p.replace("Update.sh")'
bash Update.sh
```

Then use only `bash Update.sh` for subsequent updates. Do not extract the new package into a second folder or rerun setup over the installed server.

## What gets updated

The updater replaces maintained package launchers, the HTML panel, installer/helper scripts, documentation and content **templates** in the extracted package. Local changes to those maintained package files are backed up before replacement. Unknown files are retained; obsolete package files are not automatically deleted.

The installed `CS15Server-Linux` directory, custom server directories, passwords, `server.cfg`, AMXX users, panel backups, maps, statistics, logs and local settings are preserved. Updating the package does **not** reinstall the game engine, apply content templates to an existing server or repair installed WAD files. See [the existing-install WAD repair](LINUX-MINT.md#fix-an-older-installation-stopping-on-a-map-change) if that issue still applies.

Saves go into `.update-backups/<timestamp-id>/`, with a `receipt.json` listing changed and newly created files and `files/` holding previous versions. Download/archive validation completes before package files change. A replacement failure triggers restoration. If the updater process is interrupted, its journal is restored on the next `bash Update.sh` invocation before another download. Keep the backup and `.update-active.json` if recovery reports an error. This is a recovery mechanism for a sequence of file replacements, not a guarantee against disk failure or loss of power.

Only one updater can run at a time. It also checks for the package's running panel helper and a game server whose working directory is inside the package. These checks supplement the instruction to stop both first; custom service/process arrangements may not be visible to this user.

Git checkouts are deliberately rejected. For a cloned repository, stop the panel/server and use `git pull --ff-only`, resolving any local Git changes first.

## Versions and ZIP filenames

`VERSION` contains the package version, currently **1.0.1**. The updater also records the exact 40-character commit ID in `.package-update.json` after a successful update. Several commits can share one package version; the commit identifies the exact snapshot.

```bash
bash Update.sh --version   # Local version, no download
bash Update.sh --check     # Download/validate available snapshot without installing it
```

The ordinary [Linux branch ZIP](https://github.com/skillmatic87/HL-noSteam/archive/refs/heads/linux-mint-server.zip) is a moving download. Its filename is not a unique version number. The fixed [v1.0.1-linux ZIP](https://github.com/skillmatic87/HL-noSteam/archive/refs/tags/v1.0.1-linux.zip) identifies this package version. For a specific development snapshot, use a full commit ID in place of `COMMIT`:

```text
https://github.com/skillmatic87/HL-noSteam/archive/COMMIT.zip
```

The updater resolves the branch once, then downloads that exact commit's archive. A repeated update checks package bytes again, so it can repair an edited or missing package file even when the commit ID has not changed. `Setup-Linux.sh` and `scripts/server_panel.py` must still exist to identify the package folder. Opening the local panel again is required to load an updated helper.
