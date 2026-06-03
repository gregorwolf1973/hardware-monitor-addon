# Changelog

## 2.4.1
- Default CPU sample window raised from 300 ms to 3 s — calmer values, less
  influenced by the polling overhead, closer to HA's own System Monitor
- Added "CPU sample window" section to DOCS.md / DOCS.de.md explaining the
  trade-off and the observer effect

## 2.4.0
- New UI control: **CPU sample** (100 ms / 300 ms / 500 ms / 1 s / 2 s / 3 s).
  Sets how long psutil averages CPU usage for each refresh — longer = smoother
  values but the request blocks for that duration. Backend parameter
  `?cpu_ms=` (clamped 50–3000), preference stored in localStorage.

## 2.3.2
- Fix: global CPU load no longer disagrees with the per-core values. Both are
  now derived from the same 0.3 s sample (previously the global value used a
  0.3 s window while per-core measured since the previous API call).

## 2.3.1
- Revert CPU% normalization from 2.3.0 — back to raw psutil scale
  (1 core = 100%, multi-threaded processes can exceed 100%)

## 2.3.0
- CPU% per process is now normalized to whole-machine load (divided by logical
  core count). Sum of all process CPU% now matches the top CPU gauge — instead
  of the raw psutil scale where a single busy core showed as 100% and a
  multi-threaded process could exceed 100%.

## 2.2.0
- UI fully translated to English
- Added `icon.png` and `logo.png`
- New documentation: `README.md` / `README.de.md` and `DOCS.md` / `DOCS.de.md`
- Default browser locale used for timestamps (was hard-coded `de-DE`)

## 2.1.0
- Filter-Chips: Alle / HA / Host / Docker
- Refresh-Intervall einstellbar (2s, 5s, 10s, 30s, aus) — Wahl wird im Browser gespeichert
- HA Supervisor und Helper-Container (hassio_dns, hassio_audio …) per cmdline-Heuristik erkannt und benannt
- Sort- und Filter-Auswahl bleibt in localStorage gespeichert

## 2.0.0
- Umstellung auf echtes Semver (vorher mehrdeutig: 1.10 wurde als 1.1 geparst)
- Funktional identisch zu 1.11

## 1.11
- Re-Release wegen Versionsparsing: "1.10" wurde von HA u.U. als 1.1 gelesen und damit als älter als 1.09 eingestuft

## 1.10
- Container-Namen statt nur IDs: liest /proc/<pid>/root/etc/hostname und cached pro Container
- Erkennt "homeassistant" explizit als "HA Core"
- HA-Addon-Slugs erscheinen jetzt direkt im Badge (z. B. "hardware-monitor")

## 1.09
- Fix: Datenträgerliste zeigte denselben /dev/sdaX mehrfach, weil Docker einzelne Dateien (/etc/resolv.conf, /etc/hostname …) als Bind-Mounts mit eigener Mountpoint einfügt
- Dedupliziert jetzt nach Device und filtert /etc/, /run/, /proc/, /sys/, /dev/ Bind-Mounts heraus

## 1.08
- Prozessliste: Kommandozeile, User und Container-/Addon-Badge je Prozess
- Erkennt automatisch HA-Addon-Container und Docker-Container und kennzeichnet sie
- HTML-Escaping für sichere Anzeige der Cmdlines

## 1.07
- Zurück zum HA-Base-Image (Supervisor erlaubt nur ghcr.io/home-assistant/*)
- ENTRYPOINT [] umgeht den s6-Init, sodass host_pid:true funktioniert

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
