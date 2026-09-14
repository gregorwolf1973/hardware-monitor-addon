# Hardware Monitor

[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://buymeacoffee.com/gregorwolf1973)

**Deutsch** · [English](DOCS.md)

Live-Übersicht über CPU, RAM, Datenträger, Netzwerk, Temperaturen und Prozesse
— über **alle** Addons und das Host-System hinweg.

## Installation

1. Addon öffnen und **Installieren** klicken.
2. Sicherstellen, dass **Protection Mode** **AUS** ist (Info-Tab) — sonst
   blockiert der Supervisor `host_pid` und das Addon sieht nur sich selbst.
3. Addon **starten** und über die Seitenleiste (Ingress) öffnen.

## Bedienung

- **Header-Kacheln**: CPU, RAM, Swap, Netzwerk, Load-Average und Temperaturen
  auf einen Blick. CPU, RAM und Netzwerk zeichnen zusätzlich eine
  **Sparkline** der letzten Messwerte.
- **Datenträger**: Ein Eintrag pro physischem Device. Docker-Bind-Mounts auf
  einzelne Dateien (`/etc/resolv.conf`, `/etc/hostname`, …) werden gefiltert.
- **Prozesse**: Top 60 (nach CPU) vom Host.
  - **Sortierbare Spalten** — ein Klick auf die Überschrift sortiert nach PID,
    Name, CPU %, RAM, RAM % oder Swap; ein weiterer Klick auf dieselbe Spalte
    dreht die Richtung um. Der Pfeil zeigt Spalte und Richtung an, die Wahl
    merkt sich der Browser. Nur *Status* ist nicht sortierbar.
  - **Suchfeld** — filtert beim Tippen nach Prozessname und Kommandozeile,
    `/` springt hinein.
  - **Filter-Chips** — Alle / HA / Host / Docker
  - **Grouped** — fasst die Prozesse nach Addon / Container zusammen statt sie
    einzeln zu listen (eine Suche hebt die Gruppierung auf).
  - **Refresh-Intervall** — 2 s / 5 s / 10 s / 30 s / aus (im Browser gespeichert)
  - **CPU sample** — siehe nächster Abschnitt.
  - **Badges** zeigen die Quelle an: `HA Core`, `hassio_dns`, Addon-Slug,
    Docker-Containername oder Host; ein zweites Badge nennt den Benutzer, unter
    dem der Prozess läuft. Ein Klick auf die Kommandozeile klappt sie auf.
- **Pause** (der ⏸-Knopf neben der Refresh-Anzeige) hält die automatische
  Aktualisierung an; im Hintergrund-Tab passiert das automatisch.
- **Theme-Umschalter** oben rechts wechselt zwischen Dark und Light.
- **Tastenkürzel** (außerhalb von Eingabefeldern und des Swap-Dialogs):
  `/` Suchfeld fokussieren · `Leertaste` Pause / weiter · `R` sofort
  aktualisieren · `T` Theme wechseln.

## CPU-Messfenster

Der **CPU sample**-Schalter (neben *Refresh*) bestimmt, wie lange psutil die
CPU-Last für jede Messung mittelt. Standard ist **3 s**.

- **Kurze Fenster (100–500 ms)** erwischen einzelne Spitzen. Der Wert
  springt stark und liegt häufig **über** dem "echten" Mittelwert, weil das
  Polling selbst (Flask + Iterieren über ~200 `/proc/<pid>/*`-Einträge)
  genau während der Messung Last erzeugt.
- **Lange Fenster (2–3 s)** mitteln über viel mehr Idle-Zeit und passen
  besser zu anderen Tools — z. B. zeigt der eingebaute HA System Monitor
  (5‑Minuten-Aggregation) Werte, die nah an einem 3‑s-Sample liegen.

Wenn Hardware Monitor 10–15 % anzeigt, während ein anderes Tool 3–5 %
meldet, ist die Differenz hauptsächlich Beobachter-Effekt (Polling-Kosten)
plus kürzeres Messfenster. **3 s** liefert ruhigere Werte; ein längeres
**Refresh**-Intervall reduziert die Polling-Last zusätzlich.

## Swap einstellen

Ab **Home Assistant OS 15** zeigt die Swap-Kachel die eingestellte Größe und
Swappiness. **Configure** öffnet den Dialog (nur über die Seitenleiste, nicht
über den direkten Port 8200):

- **Empfehlung** (grün markiert): ungefähr so groß wie der RAM bis 4 GB,
  darüber die Hälfte, höchstens 8 GB. Ist schon viel Swap belegt, gibt es
  Luft für das Doppelte; auf SD-Karten/eMMC bleibt es bei 2 GB. Es wird nie
  mehr vorgeschlagen, als auf die Datenpartition passt – 2 GB bleiben frei.
- **Swappiness**: Home Assistant OS nutzt 1, also Swap erst bei echtem
  Speichermangel. Das ist auf SSD und Flash die richtige Einstellung.
- Eine **neue Größe gilt erst nach einem Neustart des Hosts**. Der Hinweis
  mit **Restart host…** bleibt stehen, bis er erfolgt ist. Swappiness wirkt
  sofort.

Swap überbrückt Speicherspitzen, ersetzt aber keinen RAM: Ist er dauerhaft
stark belegt, zeigt die Prozessliste (Spalte *Swap*, Ansicht *Grouped*),
welches Addon den Speicher braucht.

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
| `hassio_api`   | `true`        | Swap-Einstellungen über die Supervisor-API             |
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
