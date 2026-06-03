#!/usr/bin/env python3
"""Hardware Monitor - Flask Web GUI"""
import os
import re
import time
import platform
import psutil
from flask import Flask, jsonify, request, render_template

app = Flask(__name__)

# Cache for container hostnames (container_id -> name)
_container_name_cache = {}

def _container_hostname(container_id, pid):
    """Read container's /etc/hostname via /proc/<pid>/root – cached per container."""
    if not container_id:
        return ""
    if container_id in _container_name_cache:
        return _container_name_cache[container_id]
    name = ""
    try:
        with open(f"/proc/{pid}/root/etc/hostname") as f:
            name = f.read().strip()
    except Exception:
        pass
    _container_name_cache[container_id] = name
    return name


# cmdline → friendly name for HA system containers whose hostname is just a hex ID
HA_SUPERVISOR_CMD_HINTS = (
    ("python3 -m supervisor", "hassio_supervisor"),
    ("coredns",                "hassio_dns"),
    ("pulseaudio",             "hassio_audio"),
    ("udevd",                  "hassio_observer"),
    ("hassio-multicast",       "hassio_multicast"),
    ("hassio-cli",             "hassio_cli"),
)

_HEX_NAME = re.compile(r"^[0-9a-f]{12,}$")

def _classify(container_id, container_name, cmdline):
    """Return (source, label) tuple.

    source: host | ha_core | ha_supervisor | ha_addon | docker
    label:  human readable name to display
    """
    if not container_id:
        return "host", ""
    if container_name == "homeassistant":
        return "ha_core", "HA Core"
    # HA system containers often have hex hostnames – guess via cmdline
    if not container_name or _HEX_NAME.match(container_name):
        for hint, label in HA_SUPERVISOR_CMD_HINTS:
            if hint in cmdline:
                return "ha_supervisor", label
        return "docker", container_name or container_id
    # hassio_* containers are also part of the HA system stack
    if container_name.startswith("hassio") or container_name.startswith("hassio_"):
        return "ha_supervisor", container_name
    # everything else with a meaningful hostname → likely an addon
    return "ha_addon", container_name

# ── network delta tracking ──────────────────────────────────────
_net_last = {"time": time.time(), "sent": 0, "recv": 0}

def _net_speed():
    now = time.time()
    net = psutil.net_io_counters()
    dt = now - _net_last["time"] or 1
    tx = (net.bytes_sent - _net_last["sent"]) / dt
    rx = (net.bytes_recv - _net_last["recv"]) / dt
    _net_last.update({"time": now, "sent": net.bytes_sent, "recv": net.bytes_recv})
    return {
        "tx_bps": max(0, tx),
        "rx_bps": max(0, rx),
        "total_sent": net.bytes_sent,
        "total_recv": net.bytes_recv,
    }


# ── routes ──────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/hardware")
def hardware():
    # CPU – derive global from per-core so both share the same sample window
    cpu_per_core = psutil.cpu_percent(interval=0.3, percpu=True)
    cpu_percent = round(sum(cpu_per_core) / len(cpu_per_core), 1) if cpu_per_core else 0.0
    cpu_count_phys = psutil.cpu_count(logical=False) or 1
    cpu_count_logi = psutil.cpu_count(logical=True) or 1
    freq = psutil.cpu_freq()

    # Memory
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()

    # Disks – dedupe Docker bind-mounts that point to the same device
    disks = []
    seen_devices = set()
    SKIP_PREFIXES = ("/etc/", "/run/", "/proc/", "/sys/", "/dev/")
    for part in psutil.disk_partitions(all=False):
        if any(x in part.fstype for x in ("squash", "tmpfs", "devtmpfs", "overlay")):
            continue
        # Skip single-file bind-mounts from the container (resolv.conf, hostname, hosts ...)
        if part.mountpoint.startswith(SKIP_PREFIXES):
            continue
        # Only one entry per real device
        if part.device in seen_devices:
            continue
        try:
            usage = psutil.disk_usage(part.mountpoint)
            if usage.total < 1024 * 1024:
                continue
            seen_devices.add(part.device)
            disks.append({
                "device": part.device,
                "mountpoint": part.mountpoint,
                "fstype": part.fstype,
                "total": usage.total,
                "used": usage.used,
                "free": usage.free,
                "percent": usage.percent,
            })
        except PermissionError:
            pass

    # Network
    net = _net_speed()

    # Temperatures
    temps = []
    try:
        sensors = psutil.sensors_temperatures()
        for chip, entries in sensors.items():
            for e in entries:
                temps.append({
                    "chip": chip,
                    "label": e.label or chip,
                    "current": round(e.current, 1),
                    "high": e.high,
                    "critical": e.critical,
                })
    except Exception:
        pass

    # System
    uptime_sec = time.time() - psutil.boot_time()

    return jsonify({
        "cpu": {
            "percent": cpu_percent,
            "cores_physical": cpu_count_phys,
            "cores_logical": cpu_count_logi,
            "freq_current": round(freq.current) if freq else None,
            "freq_max": round(freq.max) if freq else None,
            "per_core": cpu_per_core,
        },
        "memory": {
            "total": mem.total,
            "used": mem.used,
            "available": mem.available,
            "percent": mem.percent,
        },
        "swap": {
            "total": swap.total,
            "used": swap.used,
            "percent": swap.percent,
        },
        "disks": disks,
        "network": net,
        "temperatures": temps,
        "system": {
            "hostname": platform.node(),
            "platform": platform.system(),
            "uptime_seconds": uptime_sec,
        },
    })


@app.route("/api/processes")
def processes():
    sort_by = request.args.get("sort", "cpu")  # name | cpu | ram
    filter_by = request.args.get("filter", "all")  # all | host | ha | docker
    try:
        limit = max(10, min(500, int(request.args.get("limit", 60))))
    except ValueError:
        limit = 60

    # diagnostic – are we in host PID namespace?
    try:
        proc_pids = [p for p in os.listdir("/proc") if p.isdigit()]
        proc_pid_count = len(proc_pids)
    except Exception:
        proc_pid_count = -1
    try:
        with open("/proc/1/comm") as f:
            pid1_name = f.read().strip()
    except Exception:
        pid1_name = "?"

    procs = []
    access_denied = 0
    for proc in psutil.process_iter(["pid", "name", "username", "cpu_percent",
                                     "memory_info", "memory_percent", "status", "cmdline"]):
        try:
            info = proc.info
            ram_mb = (info["memory_info"].rss // (1024 * 1024)) if info["memory_info"] else 0
            cmdline_list = info.get("cmdline") or []
            cmdline = " ".join(cmdline_list).strip()
            # /proc/<pid>/cgroup for docker container ID + lookup hostname
            container_id = ""
            container_name = ""
            try:
                with open(f"/proc/{info['pid']}/cgroup") as f:
                    cg = f.read()
                    m = re.search(r"docker[/-]([a-f0-9]{12,64})", cg)
                    if m:
                        container_id = m.group(1)[:12]
                        container_name = _container_hostname(container_id, info["pid"])
            except Exception:
                pass

            source, label = _classify(container_id, container_name, cmdline)
            procs.append({
                "pid": info["pid"],
                "name": info["name"] or "?",
                "user": info.get("username") or "",
                "cmdline": cmdline,
                "container": container_id,
                "container_name": container_name,
                "source": source,
                "label": label,
                "cpu": round(info["cpu_percent"] or 0, 1),
                "ram_mb": ram_mb,
                "ram_percent": round(info["memory_percent"] or 0, 1),
                "status": info["status"],
            })
        except psutil.AccessDenied:
            access_denied += 1
        except (psutil.NoSuchProcess, Exception):
            pass

    # apply filter
    if filter_by == "host":
        procs = [p for p in procs if p["source"] == "host"]
    elif filter_by == "docker":
        procs = [p for p in procs if p["source"] == "docker"]
    elif filter_by == "ha":
        procs = [p for p in procs if p["source"].startswith("ha_")]
    # else "all" → keep everything

    if sort_by == "name":
        procs.sort(key=lambda x: x["name"].lower())
    elif sort_by == "ram":
        procs.sort(key=lambda x: x["ram_mb"], reverse=True)
    else:
        procs.sort(key=lambda x: x["cpu"], reverse=True)

    return jsonify({
        "processes": procs[:limit],
        "diag": {
            "proc_pids_total": proc_pid_count,
            "pid1_name": pid1_name,
            "psutil_visible": len(procs),
            "access_denied": access_denied,
            "host_pid_active": pid1_name not in ("s6-svscan", "?") and proc_pid_count > 30,
        },
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8200))
    app.run(host="0.0.0.0", port=port, debug=False)
