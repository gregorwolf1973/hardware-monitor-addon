# Hardware Monitor – Home Assistant Add-on-Repository

**Deutsch** · [English](README.md)

[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://buymeacoffee.com/gregorwolf1973)

Live-Übersicht deines Home-Assistant-Hosts: CPU, RAM, Datenträger, Netzwerk,
Temperaturen und die Top-Prozesse aller Addons und des Host-Systems.

![logo](hardware_monitor/logo.png)

## Repository hinzufügen

In Home Assistant: **Einstellungen → Apps → App installieren → ⋮ → Repositories**
und folgende URL eintragen:

```
https://github.com/gregorwolf1973/hardware-monitor-addon
```

Danach **Hardware Monitor** installieren und über die Seitenleiste (Ingress)
öffnen.

## Funktionen

- CPU gesamt + pro Kern, Frequenz, Kernanzahl
- RAM und Swap mit Auslastungsbalken
- Swap-Größe und Swappiness in der Oberfläche einstellbar (Home Assistant OS 15+)
- Datenträger pro Device (Docker-Bind-Mount-Dubletten werden gefiltert)
- Live-Netzwerkdurchsatz (TX/RX) + Summen
- Temperatursensoren (sofern vorhanden)
- Top-Prozesse (jede Spalte sortierbar: PID, Name, CPU, RAM, RAM %, Swap), mit Swap-Nutzung pro
  Prozess, Suchfeld und Ansicht **Grouped** nach Addon
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
