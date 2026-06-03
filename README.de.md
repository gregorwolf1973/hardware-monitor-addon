# Hardware Monitor – Home Assistant Add-on-Repository

**Deutsch** · [English](README.md)

Live-Übersicht deines Home-Assistant-Hosts: CPU, RAM, Datenträger, Netzwerk,
Temperaturen und die Top-Prozesse aller Addons und des Host-Systems.

![logo](hardware_monitor/logo.png)

## Repository hinzufügen

In Home Assistant: **Einstellungen → Add-ons → Add-on Store → ⋮ → Repositories**
und folgende URL eintragen:

```
https://github.com/gregorwolf1973/hardware-monitor-addon
```

Danach **Hardware Monitor** installieren und über die Seitenleiste (Ingress)
öffnen.

## Funktionen

- CPU gesamt + pro Kern, Frequenz, Kernanzahl
- RAM und Swap mit Auslastungsbalken
- Datenträger pro Device (Docker-Bind-Mount-Dubletten werden gefiltert)
- Live-Netzwerkdurchsatz (TX/RX) + Summen
- Temperatursensoren (sofern vorhanden)
- Top-Prozesse (sortierbar nach CPU / RAM / Name)
- Filter: **Alle / HA / Host / Docker**
- Einstellbares Refresh-Intervall (2s / 5s / 10s / 30s / aus), wird im Browser
  gespeichert
- Erkennt HA Core, Supervisor-Helper (`hassio_dns`, `hassio_audio`, …) und
  Addon-Container am Namen
- Dark- / Light-Theme

## Benötigte Rechte

Das Addon braucht `host_pid: true`, um Prozesse außerhalb des eigenen Containers
zu sehen. Bei aktivem **Protection Mode** blockiert der Supervisor das — siehe
[DOCS.de.md](hardware_monitor/DOCS.de.md) für die Reparatur per Info-Tab.

## Lizenz

MIT
