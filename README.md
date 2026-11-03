# HL-noSteam

Planung und Konfiguration fuer Half-Life und Counter-Strike 1.5 mit Dedicated Servern.

Status: Bestandsaufnahme und Recherche. Spielupdates, Modinstallation und Serverbetrieb sind noch nicht umgesetzt. Die offenen Anforderungen werden mit dem Betreiber geklaert, bevor daraus eine konkrete Zielkonfiguration entsteht.

## Bestaetigter Ist-Stand

- Lokales Half-Life: **1.1.0.8**. Belege: Windows-Dateiversion von `hl.exe` und Versionsangabe in der mitgelieferten `readme.txt`.
- `hlds.exe` und eine Half-Life-Konfiguration fuer Dedicated Server sind vorhanden. Die Laufzeitversion des Servers ist noch nicht geprueft.
- Spielverzeichnisse `valve`, `tfc` und `dmc` sind vorhanden. Ein `cstrike`-Verzeichnis war bei der Bestandsaufnahme nicht vorhanden.
- Die lokale Struktur enthaelt WON-Komponenten. Herkunft, Lizenz, Sprache und Laufzeit-Build bleiben zu klaeren.
- Gewuenschter GitHub-Zielname: **skillmatic87/HL-noSteam**, oeffentlich.

Die Versionsangabe 1.1.0.8 stammt aus den lokalen Dateien; das Spiel wurde fuer diese Pruefung nicht gestartet.

## Unterlagen

- [Recherche und Umsetzungsphasen](docs/PLAN.md)
- [Offene Entscheidungen](docs/FRAGEN.md)
- [Quellen und Kompatibilitaetsgrenzen](docs/QUELLEN.md)
- [Lesende Bestandsaufnahme](scripts/Get-HalfLifeInventory.ps1)

Dieses Repository versioniert Projektdokumentation und eigene Skripte. Die bestehende Spielinstallation, Installationsprotokolle, Zugangsdaten, Downloads und Spielassets werden nicht veroeffentlicht. Es enthaelt derzeit keine lauffaehige Serverbereitstellung.
