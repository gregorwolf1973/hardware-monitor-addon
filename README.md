# Hardware Monitor – Home Assistant Add-on Repository

[Deutsch](README.de.md) · **English**

[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://buymeacoffee.com/gregorwolf1973)

Live overview of your Home Assistant host: CPU, RAM, disks, network, temperatures
and the top processes across **all** addons and the host system.

![logo](hardware_monitor/logo.png)

## Add this repository

In Home Assistant: **Settings → Apps → Install app → ⋮ → Repositories** and add

```
https://github.com/gregorwolf1973/hardware-monitor-addon
```

Then install **Hardware Monitor** and open it through the side panel (Ingress).

## Features

- CPU total + per-core load, frequency, core counts
- RAM and swap with usage bars
- Swap size and swappiness configurable from the UI (Home Assistant OS 15+)
- Disk usage per device (Docker bind-mount duplicates filtered out)
- Live network throughput (TX/RX) + totals
- Temperature sensors (where available)
- Top processes (every column sortable: PID, name, CPU, RAM, RAM %, swap), with per-process swap usage,
  search box and a **Grouped** view per add-on
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
