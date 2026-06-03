# Hardware Monitor – Home Assistant Add-on Repository

[Deutsch](README.de.md) · **English**

Live overview of your Home Assistant host: CPU, RAM, disks, network, temperatures
and the top processes across **all** addons and the host system.

![logo](hardware_monitor/logo.png)

## Add this repository

In Home Assistant: **Settings → Add-ons → Add-on Store → ⋮ → Repositories** and add

```
https://github.com/gregorwolf1973/hardware-monitor-addon
```

Then install **Hardware Monitor** and open it through the side panel (Ingress).

## Features

- CPU total + per-core load, frequency, core counts
- RAM and swap with usage bars
- Disk usage per device (Docker bind-mount duplicates filtered out)
- Live network throughput (TX/RX) + totals
- Temperature sensors (where available)
- Top processes (sortable by CPU / RAM / name)
- Filter chips: **All / HA / Host / Docker**
- Configurable refresh interval (2s / 5s / 10s / 30s / off), stored in your browser
- Recognizes Home Assistant Core, Supervisor helpers (`hassio_dns`, `hassio_audio`, …)
  and Add-on containers by name
- Dark / light theme

## Required permissions

The addon needs `host_pid: true` to see processes outside its own container.
If **Protection Mode** is enabled, the Supervisor blocks this — see
[DOCS.md](hardware_monitor/DOCS.md) for the one-click fix in the addon's
Info tab.

## License

MIT
