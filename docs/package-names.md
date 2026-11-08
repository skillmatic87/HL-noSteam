# Lowercase package names

Maintained package files and folders use lowercase names, including the public entry points:

```bash
bash setup-linux.sh
bash start-panel.sh
bash start-server.sh
bash update.sh
```

Documentation, PowerShell scripts, the HTML panel and their package references use the same rule. This makes names copied from the instructions work on a case-sensitive Linux filesystem.

An existing installed game server remains in its original directory, such as `CS15Server-Linux`. Its private files and engine interfaces, including `Start-CS15.sh`, `ADMIN.local.txt` and `SND-LIST.CFG`, keep their existing names for compatibility. Use the lowercase package launchers above to start it; do not rename those installed files manually.

The ZIP updater handles the maintained package-name migration separately from the installed game files. Stop the server and panel helper before updating; see [updating](updating.md).
