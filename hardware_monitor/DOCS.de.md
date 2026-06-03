# Hardware Monitor

**Deutsch** · [English](DOCS.md)

Live-Übersicht über CPU, RAM, Datenträger, Netzwerk, Temperaturen und Prozesse
— über **alle** Addons und das Host-System hinweg.

## Installation

1. Addon öffnen und **Installieren** klicken.
2. Sicherstellen, dass **Protection Mode** **AUS** ist (Info-Tab) — sonst
   blockiert der Supervisor `host_pid` und das Addon sieht nur sich selbst.
3. Addon **starten** und über die Seitenleiste (Ingress) öffnen.

## Bedienung

- **Header-Kacheln**: CPU, RAM, Netzwerk, Temperaturen auf einen Blick.
- **Datenträger**: Ein Eintrag pro physischem Device. Docker-Bind-Mounts auf
  einzelne Dateien (`/etc/resolv.conf`, `/etc/hostname`, …) werden gefiltert.
- **Prozesse**: Top 60, sortierbar nach CPU, RAM oder Name.
  - **Filter-Chips** — Alle / HA / Host / Docker
  - **Refresh-Intervall** — 2 s / 5 s / 10 s / 30 s / aus (im Browser gespeichert)
  - **Badges** zeigen die Quelle an: `HA Core`, `hassio_dns`, Addon-Slug,
    Docker-Containername oder Host.
- **Theme-Umschalter** oben rechts wechselt zwischen Dark und Light.

## Warum fehlen Prozesse?

Wenn das gelbe Diagnose-Banner erscheint ("host_pid INAKTIV — Container sieht
nur sich selbst"), blockiert der Protection Mode das Namespace-Sharing.
Im **Info**-Tab des Addons **Protection Mode** ausschalten und Addon neu
starten.

PID 1 sollte dann ein Host-Prozess sein (`init`, `systemd`, …) und die
Gesamtzahl der Prozesse im dreistelligen Bereich.

## Berechtigungen

| Option         | Wert          | Grund                                                  |
| -------------- | ------------- | ------------------------------------------------------ |
| `host_pid`     | `true`        | Prozesse außerhalb des Containers sehen                |
| `host_network` | `true`        | Echte Host-Netzwerkzähler lesen                        |
| `hassio_role`  | `manager`     | Notwendig für Panel + erweiterte Supervisor-APIs       |
| `privileged`   | `SYS_PTRACE`  | `/proc/<pid>/cgroup` und Kommandozeilen lesen          |
| `apparmor`     | `false`       | Zugriff auf `/proc/<pid>/root/etc/hostname`            |

`full_access` wird **nicht** verwendet — kollidiert mit `host_pid` und
verhindert den Containerstart.

## Fehlersuche

| Symptom                                                   | Lösung                                         |
| --------------------------------------------------------- | ---------------------------------------------- |
| Nur ~8 Prozesse sichtbar                                  | Protection Mode ausschalten, Addon neu starten |
| Addon startet nicht, Log: "can only run as pid 1"         | Bereits in v1.07+ behoben (umgeht s6-overlay)  |
| Gleicher `/dev/sdaX` mehrfach in der Liste                | Bereits in v1.09+ behoben                      |
| Version 1.10 wird nicht als Update erkannt                | Auf v2.0.0+ updaten (korrektes Semver)         |
