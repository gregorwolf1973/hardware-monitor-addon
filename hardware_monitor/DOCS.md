# Hardware Monitor

[Deutsch](DOCS.de.md) · **English**

Live overview of CPU, RAM, disks, network, temperatures and processes — across
**all** addons and the host system.

## Installation

1. Open the addon and click **Install**.
2. Make sure **Protection Mode** is **OFF** (Info tab) — otherwise the
   Supervisor blocks `host_pid` and the addon only sees its own processes.
3. **Start** the addon and open it via the side panel (Ingress).

## How to use

- **Header cards**: CPU, RAM, network, temperatures at a glance.
- **Disks**: One entry per physical device. Docker bind-mounts that point to
  single files (`/etc/resolv.conf`, `/etc/hostname`, …) are filtered out.
- **Processes**: Top 60 sorted by CPU, RAM or name.
  - **Filter chips** — All / HA / Host / Docker
  - **Refresh interval** — 2 s / 5 s / 10 s / 30 s / off (stored in browser)
  - **Badges** identify the source: `HA Core`, `hassio_dns`, addon slug,
    docker container name, or host.
- **Theme toggle** in the top-right switches between dark and light.

## Why are some processes missing?

If you see a yellow diagnostic banner ("host_pid INACTIVE — container only sees
itself"), the Supervisor's Protection Mode is blocking namespace sharing.
Open the addon's **Info** tab and toggle **Protection Mode** off, then restart
the addon.

PID 1 should show as a host process (`init`, `systemd`, …) and the total
process count should be in the hundreds, not single digits.

## Permissions

| Setting        | Value         | Reason                                                |
| -------------- | ------------- | ----------------------------------------------------- |
| `host_pid`     | `true`        | See processes outside the container                   |
| `host_network` | `true`        | Read real host network counters                       |
| `hassio_role`  | `manager`     | Required for the panel + extended Supervisor APIs     |
| `privileged`   | `SYS_PTRACE`  | Read `/proc/<pid>/cgroup` and command lines           |
| `apparmor`     | `false`       | Allow access to `/proc/<pid>/root/etc/hostname`       |

`full_access` is **not** used — it conflicts with `host_pid` and stops the
container from starting.

## Troubleshooting

| Symptom                                                | Fix                                            |
| ------------------------------------------------------ | ---------------------------------------------- |
| Only ~8 processes visible                              | Turn off Protection Mode, restart the addon    |
| Addon does not start, log says "can only run as pid 1" | Already fixed in v1.07+ (bypasses s6-overlay)  |
| Same `/dev/sdaX` listed multiple times                 | Already fixed in v1.09+                        |
| Version 1.10 not detected as update                    | Upgrade to v2.0.0+ (proper semver)             |
