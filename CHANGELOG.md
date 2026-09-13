# Changelog

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

