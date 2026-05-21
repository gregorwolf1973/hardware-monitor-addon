# Changelog

## 1.06
- Basisimage gewechselt: weg von HAs s6-Image (Konflikt mit host_pid), hin zu python:3.12-alpine
- s6-overlay verlangt zwingend PID 1 — mit host_pid:true unmöglich
- run.sh: plain sh statt bashio (war ohne Optionen ohnehin überflüssig)

## 1.05
- full_access entfernt (kollidierte mit host_pid → Addon startete nicht)
- Privileg-Caps auf SYS_PTRACE reduziert (analog Glances)
- hassio_role: manager ergänzt

## 1.04
- Korrekter Hinweis im Diagnose-Banner: Protection Mode ausschalten (Info-Tab) statt Neuinstallation

## 1.03
- Diagnose-Banner zeigt jetzt an, ob host_pid effektiv ist (PID-1-Check + /proc-Auswertung)
- Falls inaktiv: konkrete Reparatur-Anleitung in der UI

## 1.02
- Erweiterte Privilegien (full_access, SYS_ADMIN, DAC_READ_SEARCH) damit Host-Prozesse zuverlässig sichtbar werden

## 1.01
- Fix: host_pid aktiviert — jetzt werden alle Prozesse aller Addons und des Host-Systems angezeigt

## 1.00
- Erstveröffentlichung
- CPU-Auslastung gesamt und pro Kern
- RAM- und Swap-Anzeige
- Datenträger-Übersicht mit Füllstandsbalken
- Netzwerkdurchsatz (live KB/s – MB/s)
- Temperatursensoren (falls verfügbar)
- Prozessliste: Top 60, sortierbar nach Name / CPU / RAM
- Auto-Refresh alle 5 Sekunden
- Dark- / Light-Theme
