# Recherche und Umsetzungsphasen

Stand: 2026-11-03. Dies ist ein Arbeitsplan mit offenen Entscheidungen, keine bereits beschlossene Serverarchitektur.

## 1. Installation und Updatepfade klaeren

Erledigt: `hl.exe` und die mitgelieferte Readme nennen **1.1.0.8**. `hlds.exe` liegt vor; CS 1.5 ist im untersuchten Stammordner nicht installiert. Die bestehende `valve/server.cfg` enthaelt grundlegende Dedicated-Server-Einstellungen, jedoch noch keine fuer diesen Auftrag festgelegte Konfiguration.

Naechste Schritte nach Klaerung von Installationsumfang, Sprache und Erhaltungswunsch:

1. Bestand und eigene Einstellungen sichern; Zielverzeichnis festlegen.
2. Fuer den klassischen Retail/WON-Zweig den Patch **1.1.1.0** als Kandidaten pruefen. Das CS-1.5-Archiv empfiehlt diese Windows-Version ausdruecklich.
3. Sprachpassendes Paket, Herkunft, Dateigroesse und Hashes dokumentieren. Ein selbst berechneter SHA-256-Hash dient der Nachvollziehbarkeit; ohne unabhaengigen Referenzwert beweist er keine Authentizitaet.
4. Update zunaechst in einer vereinbarten Testinstallation anwenden und Client-/Server-Build danach zur Laufzeit pruefen.

Der aktuelle Steam-Zweig ist ein eigener Updatepfad. Valve nennt die Anniversary-Ausgabe die weiter unterstuetzte Ausgabe und bietet `steam_legacy` als Kompatibilitaetszweig an. Das ist kein direkt auf eine Retail-Installation anzuwendender Patch. Die konkrete aktuell ausgelieferte Steam-Buildnummer wurde hier nicht bestimmt.

## 2. Counter-Strike 1.5 als Mod

Kandidat: `Ch0wW/counterstrike-betas`, Branch `cs15_retail`. Das Archiv nennt Windows und Linux und empfiehlt Windows Half-Life 1.1.1.0 bzw. Linux HLDS 3.1.1.0. Alternative Archivquelle: der CS-1.5-Modinstaller bei ModDB.

Nach Freigabe des Installationsumfangs: Paket und unveraenderte Modstruktur pruefen, geeignetes Zielverzeichnis festlegen, installieren und Start, Mapwechsel sowie Clientverbindung testen. Eine Installation mit CS-1.6-Serverbibliotheken wuerde den gewuenschten Stand nicht automatisch erhalten.

## 3. Dedicated-Server-Grundlage auswaehlen

| Kandidat | Belegter Umfang | Noch offen |
| --- | --- | --- |
| Vorhandenes Windows-HLDS | `hlds.exe` und `valve/server.cfg` lokal vorhanden | Build, Update, Laufzeit und Mod-/Plugin-Kompatibilitaet |
| `Ch0wW/docker-hlds-won2` | Projekt fuer HLDS 1.1.1.0/Protokoll 46, CS 1.5 und weitere historische Mods | Eignung fuer gewuenschten Host und tatsaechlicher Funktionstest; HLDM-Dateiumfang gesondert pruefen |
| Aktuelles Steam-HLDS | Separater moderner Betriebsweg | Gewuenschter Clientzweig und CS-1.5-Kompatibilitaet erst bestimmen |

Das WON2-Projekt dokumentiert eine andere Protokollbasis als Steam-Clients. Die Client-/Server-Paarung muss deshalb vor der Wahl von Plugins und Hosting feststehen. Das Projekt verwendet ein altes Debian-8-i386-Containerumfeld; Wartung und Internetbetrieb sind bei der Auswahl konkret zu bewerten. Ein Container allein modernisiert die historische Engine nicht.

Falls zwei gleichzeitige Server gewuenscht sind, werden separate Prozesse/Instanzen, getrennte Konfigurationen, Logs und unterschiedliche Ports geplant. Ports, Spielerzahlen, Karten und Regeln werden nach den Antworten festgelegt. Firewall, Router und Autostart sind noch nicht eingerichtet.

## 4. Erweiterungen einzeln erproben

| Wunsch | Recherche-/Testkandidat | Voraussetzung |
| --- | --- | --- |
| Adminrechte und Pluginladung | GoldSrc-Metamod plus passendes AMX Mod X | Version auf tatsaechlichem HLDS testen |
| StatsMe | Originales StatsMe oder nach Ruecksprache StatsX/andere Alternative | Originalwunsch, Quellen und benoetigte Statistikwerte klaeren |
| Votemap | AMXX-Mapchooser; RTV/Nominierungen ggf. zusaetzlich | Gewuenschten Abstimmungsablauf und alte AMXX-Version beruecksichtigen |
| Chat-Sounds | Geeignetes AMXX-SaySounds-Plugin oder eigenes kleines Plugin | Konkrete Quelle, Abhaengigkeiten, Trigger, Dateien und Rechte offen |
| Serveruebergreifende Rangliste | HLstatsX CE oder PsychoStats untersuchen | Logformat und stabile Spieleridentitaet auf gewaehltem Zweig nachweisen |

Wichtige Kompatibilitaetsgrenze: Die FAQ von `docker-hlds-won2` verlangt **AMXX 1.8.2 oder aelter**. Die aktuelle AMXX-Downloadseite fuehrt Version 1.10; daraus folgt keine Kompatibilitaet mit diesem WON2-Setup. Moderne Module mit CS-1.6-/ReAPI-Abhaengigkeit werden nicht ungeprueft fuer CS 1.5 uebernommen.

Fuer originales StatsMe und ein geeignetes SaySounds-Paket ist noch kein Installationskandidat abschliessend verifiziert. Fuer HLstatsX weist das archivierte NomisCZ-Projekt auf den A1mDev-Fork hin; die Funktion mit genau dieser historischen Spielversion ist noch nicht nachgewiesen.

## 5. Leaderboard nach Definition von global entwerfen

Moeglicher Datenfluss, falls eine Rangliste fuer eigene Server mit Website gewuenscht wird:

`HLDS-Spielereignisse -> Logauswertung -> Datenbank -> Ranglisten-Website`

Das ist eine Option, keine zugesagte Integration. Zuerst reale Beispiellogs beider Spiele erfassen und Ereignisse sowie wiedererkennbare Spieler-IDs pruefen. Anschliessend Logparser, Datenbank, Hosting, Punkteformel und gegebenenfalls Anzeigen im Spiel auswaehlen. Vergleichbarkeit von HLDM und CS sowie Wiederverbindungen und Namensaenderungen testen. Zugangsdaten und echte Spielerdaten bleiben ausserhalb des oeffentlichen Repositorys.

## 6. Abnahme vor regulaerem Betrieb

- Nachweis des gewuenschten Client- und Server-Builds.
- Verbindung mit den tatsaechlich verwendeten Clients; getrennte Pruefung fuer HLDM und CS 1.5.
- Start, Neustart, mehrere Mapwechsel und vereinbarte gleichzeitige Instanzen.
- Pluginladung und Fehlerlogs; jede Erweiterung einzeln zuschalten.
- Votemap-Ablauf, Adminrechte, Sounddownload und Chat-Trigger nach den vereinbarten Regeln.
- Statistikereignisse mit bekannten Testaktionen vergleichen; Wiederverbindung ohne doppelte Spieler, keine doppelt gezaehlten Logs.
- Sicherung und Wiederherstellung pruefen; oeffentliche Erreichbarkeit erst pruefen, wenn dieser Betriebsmodus gewuenscht ist.

Noch nicht ausgefuehrt: Downloads von Spielpaketen, Installation, Laufzeittests, Portfreigaben, Hosting-Bestellungen und Serverbereitstellung.
