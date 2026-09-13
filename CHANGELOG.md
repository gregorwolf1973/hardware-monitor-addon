# Changelog

## 2.6.0

- Klarnamen statt Prozessnamen. "python3" heisst jetzt "Home Assistant",
  "MainThread" heisst "Matter Server", ein Firefox-Kindprozess heisst
  "Firefox Tab". Aussagekraeftige Namen wie mariadb oder dockerd bleiben
  unveraendert. Der urspruengliche Name steht klein daneben und im Tooltip.
- Addon-Badges ohne Repository-Kuerzel: aus "49e24ccc-firefox" wird
  "Firefox", aus "cebe7a76-hassio-google-drive-backup" wird
  "Google Drive Backup".
- Neue Ansicht "Grouped": eine Zeile je Addon mit Summe aus CPU, RAM und
  Swap sowie der Anzahl der Prozesse. Aufklappbar zu den groessten
  Einzelprozessen. Die Summen gelten fuer alle Prozesse der Gruppe, nicht
  nur fuer die angezeigten.
- Benutzerspalte zeigt den Namen statt der nackten UID, ausgelesen aus dem
  Container des jeweiligen Prozesses.
- Legende erklaert die Badges.
- Die Suche findet jetzt auch Klarnamen und Addon-Namen.

## 2.5.0

- Neu: Spalte "Swap" in der Prozessliste. Sie zeigt, wie viel Swap jeder
  einzelne Prozess belegt, und laesst sich per Klick auf die Spalte sortieren.
  Damit ist auf einen Blick sichtbar, wer den Swap fuellt.
- Prozesse mit Swap-Nutzung werden hervorgehoben, Prozesse ohne zeigen einen
  Strich.
- Die Diagnosezeile nennt zusaetzlich die Summe des zugeordneten Swaps.
- Die Werte stammen aus VmSwap in /proc/<pid>/status, also einer einzelnen
  kleinen Datei pro Prozess. Die Prozessliste bleibt dadurch schnell.

## 2.4.4

- Fix: Absicherung gegen einen Startabsturz. Beim Binden des Webservers
  fragt Python den Hostnamen per Reverse-DNS ab. Liefert der DNS-Server
  einen Namen, der kein gültiges UTF-8 ist, warf das einen
  UnicodeDecodeError und das Addon startete nicht (Supervisor-Status
  "error"). Die Abfrage ist jetzt gekapselt.

