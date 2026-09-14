#!/usr/bin/env python3
"""Hardware Monitor - Flask Web GUI"""
import os
import re
import time
import platform
import psutil
import socket
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
    # CPU – derive global from per-core so both share the same sample window.
    # Sample duration is configurable via ?cpu_ms= (50..3000), default 3000 ms.
    try:
        cpu_ms = int(request.args.get("cpu_ms", 3000))
    except ValueError:
        cpu_ms = 3000
    cpu_ms = max(50, min(3000, cpu_ms))
    cpu_per_core = psutil.cpu_percent(interval=cpu_ms / 1000.0, percpu=True)
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
    try:
        load1, load5, load15 = os.getloadavg()
    except (OSError, AttributeError):
        load1 = load5 = load15 = None

    return jsonify({
        "cpu": {
            "percent": cpu_percent,
            "cores_physical": cpu_count_phys,
            "cores_logical": cpu_count_logi,
            "freq_current": round(freq.current) if freq else None,
            "freq_max": round(freq.max) if freq else None,
            "per_core": cpu_per_core,
            "sample_ms": cpu_ms,
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
            "loadavg": [load1, load5, load15] if load1 is not None else None,
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
    swap_total_mb = 0
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

            swap_mb = _swap_mb(info["pid"])
            swap_total_mb += swap_mb

            source, label = _classify(container_id, container_name, cmdline)
            addon = "" if source == "host" else _addon_display(label or container_name)
            display = _display_name(info["name"], cmdline, addon)
            procs.append({
                "pid": info["pid"],
                "name": info["name"] or "?",
                "user": _username(info["pid"], info.get("username") or "", container_id),
                "cmdline": cmdline,
                "container": container_id,
                "container_name": container_name,
                "source": source,
                "label": label,
                "addon": addon,
                "display": display,
                "cpu": round(info["cpu_percent"] or 0, 1),
                "ram_mb": ram_mb,
                "ram_percent": round(info["memory_percent"] or 0, 1),
                "swap_mb": swap_mb,
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
    elif sort_by == "swap":
        procs.sort(key=lambda x: x["swap_mb"], reverse=True)
    else:
        procs.sort(key=lambda x: x["cpu"], reverse=True)

    groups = {}
    for p in procs:
        key = p["container_name"] or p["container"] or "host"
        g = groups.get(key)
        if g is None:
            g = groups[key] = {
                "key": key,
                "label": p["addon"] or ("Host" if p["source"] == "host" else key),
                "source": p["source"],
                "count": 0, "cpu": 0.0, "ram_mb": 0, "ram_percent": 0.0, "swap_mb": 0,
                "top": [],
            }
        g["count"] += 1
        g["cpu"] += p["cpu"]
        g["ram_mb"] += p["ram_mb"]
        g["ram_percent"] += p["ram_percent"]
        g["swap_mb"] += p["swap_mb"]
        if len(g["top"]) < 10:      # procs is already sorted, so this is the top of the group
            g["top"].append(p)

    group_key = {"name": lambda g: g["label"].lower(), "ram": lambda g: g["ram_mb"],
                 "swap": lambda g: g["swap_mb"]}.get(sort_by, lambda g: g["cpu"])
    group_list = sorted(groups.values(), key=group_key, reverse=(sort_by != "name"))
    for g in group_list:
        g["cpu"] = round(g["cpu"], 1)
        g["ram_percent"] = round(g["ram_percent"], 1)

    return jsonify({
        "processes": procs[:limit],
        "groups": group_list,
        "diag": {
            "proc_pids_total": proc_pid_count,
            "pid1_name": pid1_name,
            "psutil_visible": len(procs),
            "access_denied": access_denied,
            "host_pid_active": pid1_name not in ("s6-svscan", "?") and proc_pid_count > 30,
            "swap_accounted_mb": swap_total_mb,
        },
    })


# ── Readable names ──────────────────────────────────────────────
# Words that should not be title-cased but written the way people write them
_ACRONYMS = {
    "ha": "HA", "ssh": "SSH", "ftp": "FTP", "mqtt": "MQTT", "dns": "DNS",
    "nas": "NAS", "tv": "TV", "sql": "SQL", "sqlite": "SQLite", "db": "DB",
    "npm": "NPM", "pdf": "PDF", "ocr": "OCR", "api": "API", "id": "ID",
    "vpn": "VPN", "usb": "USB", "cpu": "CPU", "os": "OS", "ui": "UI",
    "2fa": "2FA", "totp": "TOTP", "ip": "IP", "url": "URL", "av": "AV",
}
# Names that are technically correct but say nothing on their own
_NAME_MAP = {
    "homeassistant": "Home Assistant",
    "supervisor": "Supervisor",
    "hassio": "Supervisor",
}
# A process called like this tells us nothing – look at the command line instead
_GENERIC_NAMES = {
    "python", "python2", "python3", "node", "nodejs", "java", "sh", "bash",
    "dash", "ash", "perl", "ruby", "php", "php-fpm", "exe", "start.sh",
    "run.sh", "entrypoint.sh", "docker-init", "tini",
}
_THREADISH = re.compile(r"^(?:mainthread|thread-\d+|worker(?:-\d+)?|tokio-runtime.*)$", re.I)
_ADDON_PREFIX = re.compile(r"^(?:[0-9a-f]{8}[-_]|core[-_]|local[-_]|addon[-_])")
_HASSIO_PREFIX = re.compile(r"^hassio[-_]")
_PY_MODULE = re.compile(r"\bpython[\d.]*\s+(?:-[A-Za-z]+\s+)*-m\s+([A-Za-z0-9_.]+)")
_NODE_PKG = re.compile(r"/node_modules/((?:@[\w.-]+/)?[\w.-]+)/")
_SCRIPT = re.compile(r"([\w.-]+\.(?:py|js|mjs|sh|pl|rb))(?:\s|$)")


def _prettify(raw: str) -> str:
    """'google-drive-backup' -> 'Google Drive Backup', 'sqlite-web' -> 'SQLite Web'."""
    words = [w for w in re.split(r"[-_\s]+", (raw or "").strip()) if w]
    out = []
    for w in words:
        lw = w.lower()
        if lw in _ACRONYMS:
            out.append(_ACRONYMS[lw])
        elif w.islower():
            out.append(w[:1].upper() + w[1:])
        else:
            out.append(w)
    return " ".join(out)


def _addon_display(raw: str) -> str:
    """Container hostname -> addon name: '49e24ccc-firefox' -> 'Firefox'.

    The eight hex characters are the add-on repository, not part of the name.
    """
    if not raw:
        return ""
    n = _HASSIO_PREFIX.sub("", _ADDON_PREFIX.sub("", raw))
    if n.lower() in _NAME_MAP:
        return _NAME_MAP[n.lower()]
    return _prettify(n) or _prettify(raw)


def _display_name(name: str, cmdline: str, addon: str) -> str:
    """A name that says what the process actually is.

    'python3' with '-m homeassistant' becomes 'Home Assistant', a Firefox
    child process becomes 'Firefox Tab'. Names that are already meaningful
    (mariadb, dockerd, crowdsec) are kept unchanged.
    """
    n = (name or "?").strip()
    low = n.lower()
    cl = cmdline or ""

    if "-contentproc" in cl:
        if "webextensions" in low:
            return "Firefox Extensions"
        if "-isForBrowser" in cl:
            return "Firefox Tab"
        return "Firefox Helper"

    if low in _GENERIC_NAMES or _THREADISH.match(n):
        m = _PY_MODULE.search(cl)
        if m:
            mod = m.group(1).split(".")[-1]
            return _NAME_MAP.get(mod.lower(), _prettify(mod))
        m = _NODE_PKG.search(cl)
        if m:
            return _prettify(m.group(1).lstrip("@").split("/")[-1])
        m = _SCRIPT.search(cl)
        if m:
            return m.group(1)
        if addon:
            return addon
    return n


_user_cache: dict = {}


def _username(pid, raw_user: str, container_id: str) -> str:
    """Resolve a bare UID via the passwd file of the process' own container."""
    raw_user = (raw_user or "").strip()
    if not raw_user.isdigit():
        return raw_user
    key = (container_id, raw_user)
    if key in _user_cache:
        return _user_cache[key]
    resolved = raw_user
    try:
        with open(f"/proc/{pid}/root/etc/passwd") as f:
            for line in f:
                parts = line.split(":")
                if len(parts) > 2 and parts[2] == raw_user:
                    resolved = parts[0]
                    break
    except OSError:
        pass
    _user_cache[key] = resolved
    return resolved


def _swap_mb(pid: int) -> int:
    """Swap used by one process, in MB, from /proc/<pid>/status.

    VmSwap is the cheap way to get this – unlike smaps it is a single small
    read per process. Kernel threads and processes without swapped pages have
    no VmSwap line and count as 0.
    """
    try:
        with open(f"/proc/{pid}/status") as f:
            for line in f:
                if line.startswith("VmSwap:"):
                    return int(line.split()[1]) // 1024
    except (OSError, ValueError, IndexError):
        pass
    return 0


# ── Swap configuration (Home Assistant OS) ───────────────────────
# HAOS 15+ exposes the swap file size and swappiness through the Supervisor
# (GET/POST /os/config/swap). A new size takes effect after a host reboot.
SUPERVISOR_URL = os.environ.get("SUPERVISOR_URL", "http://supervisor")
# The Supervisor's ingress proxy. With host_network the app also listens on the
# LAN without any login, so everything that changes the host must come through
# ingress, i.e. from a signed-in Home Assistant user.
INGRESS_PROXY_IPS = {"172.30.32.2"}
SWAP_SIZE_RE = re.compile(r"^(\d+)([KMG])?$", re.I)
SWAP_MAX_BYTES = 16 * 1024 ** 3
SWAP_MIN_FREE_AFTER = 2 * 1024 ** 3      # keep this much of the data disk free
SWAP_STEPS_G = (1, 2, 4, 6, 8)           # recommendations land on one of these
_UNIT = {"": 1, "K": 1024, "M": 1024 ** 2, "G": 1024 ** 3}


class SupervisorError(Exception):
    def __init__(self, message, status=502):
        super().__init__(message)
        self.status = status


def _supervisor(method, path, payload=None, timeout=15):
    """Call the Supervisor API; returns the 'data' member or raises."""
    import json
    import urllib.error
    import urllib.request
    token = os.environ.get("SUPERVISOR_TOKEN", "")
    if not token:
        raise SupervisorError("No Supervisor token - hassio_api is not enabled for this add-on", 503)
    body = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(SUPERVISOR_URL + path, data=body, method=method, headers={
        "Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        try:
            msg = json.loads(e.read() or b"{}").get("message") or str(e)
        except ValueError:
            msg = str(e)
        raise SupervisorError(msg, 404 if e.code == 404 else 502)
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise SupervisorError(f"Supervisor not reachable: {e}", 503)
    if data.get("result") not in (None, "ok"):
        raise SupervisorError(data.get("message") or "Supervisor refused the request")
    return data.get("data") or {}


def parse_swap_size(text):
    """'4G' -> bytes; '' -> None (HAOS default); raises ValueError."""
    t = str(text or "").strip()
    if not t:
        return None
    m = SWAP_SIZE_RE.match(t)
    if not m:
        raise ValueError("Size must be a number with an optional unit K, M or G, e.g. 4G")
    return int(m.group(1)) * _UNIT[(m.group(2) or "").upper()]


def recommend_swap(ram_bytes, swap_used_bytes, data_free_bytes, storage):
    """Suggested (size string, swappiness, reasons).

    Rule of thumb for a Home Assistant box: swap about the size of RAM up to
    4 GB, half of RAM above that, never more than 8 GB. If the swap already in
    use is more than half of that, leave room for twice the current use. Keep
    at least SWAP_MIN_FREE_AFTER free on the data disk. On SD cards / eMMC
    smaller, because every page written wears the flash.
    """
    gib = 1024 ** 3
    ram_g = max(1, round(ram_bytes / gib))
    size_g = ram_g if ram_g <= 4 else max(4, ram_g // 2)
    reasons = [f"{ram_g} GB RAM: swap about the size of RAM" if ram_g <= 4
               else f"{ram_g} GB RAM: half of RAM is plenty"]
    used_g = swap_used_bytes / gib
    if used_g * 2 > size_g:
        size_g = int(-(-used_g * 2 // 1))
        reasons.append(f"{used_g:.1f} GB swap already in use - room for twice that")
    if storage == "sd":
        size_g = min(size_g, 2)
        reasons.append("SD card / eMMC: kept small to limit flash wear")
    # snap up to a familiar step, so the suggestion is 4 GB rather than 3 or 7
    size_g = next((s for s in SWAP_STEPS_G if s >= size_g), SWAP_STEPS_G[-1])
    if data_free_bytes:
        fits = int((data_free_bytes - SWAP_MIN_FREE_AFTER) // gib)
        if fits < size_g:
            size_g = max([s for s in SWAP_STEPS_G if s <= fits] or [0])
            reasons.append("limited by free space on the data disk")
    # HAOS ships swappiness 1: swap only under real memory pressure. On flash
    # storage that is exactly right; there is no reason to swap earlier.
    return (f"{size_g}G" if size_g > 0 else "0"), 1, reasons


def _data_storage_kind():
    """'ssd' | 'hdd' | 'sd' | 'unknown' for the disk holding /data."""
    try:
        dev = ""
        best = ""
        for part in psutil.disk_partitions(all=False):
            mp = part.mountpoint
            if ("/data" == mp or "/data".startswith(mp.rstrip("/") + "/") or mp == "/") and len(mp) > len(best):
                best, dev = mp, part.device
        name = os.path.basename(os.path.realpath(dev)) if dev else ""
        if name.startswith("mmcblk"):
            return "sd"
        disk = re.sub(r"(p?\d+)$", "", name) if not name.startswith("nvme") else re.sub(r"p\d+$", "", name)
        if name.startswith("nvme"):
            return "ssd"
        with open(f"/sys/block/{disk}/queue/rotational") as f:
            return "hdd" if f.read().strip() == "1" else "ssd"
    except (OSError, ValueError):
        return "unknown"


def _from_ingress():
    return request.remote_addr in INGRESS_PROXY_IPS


def _write_guard():
    """None if a state-changing request may proceed, else an error response.

    Only through ingress (a signed-in HA user), and only as JSON with our own
    header - a cross-site form or fetch cannot set that without a CORS
    preflight, which this app never answers."""
    if not _from_ingress():
        return jsonify({"error": "Changes are only allowed through the Home Assistant sidebar (ingress)."}), 403
    if request.headers.get("X-HM-Action") != "1" or not request.is_json:
        return jsonify({"error": "Bad request"}), 400
    return None


@app.route("/api/swap/config")
def swap_config():
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    try:
        data_free = psutil.disk_usage("/data").free
    except OSError:
        data_free = 0
    storage = _data_storage_kind()
    rec_size, rec_swappiness, reasons = recommend_swap(mem.total, swap.used, data_free, storage)
    out = {
        "available": False, "reason": "", "swap_size": None, "swappiness": None,
        "ram_total": mem.total, "swap_total": swap.total, "swap_used": swap.used,
        "data_free": data_free, "storage": storage,
        "recommended": {"swap_size": rec_size, "swappiness": rec_swappiness, "reasons": reasons},
        "reboot_required": False, "can_change": _from_ingress(),
        "max_bytes": min(SWAP_MAX_BYTES, max(0, data_free - SWAP_MIN_FREE_AFTER)) if data_free else SWAP_MAX_BYTES,
    }
    try:
        cfg = _supervisor("GET", "/os/config/swap")
        out.update(available=True, swap_size=cfg.get("swap_size"), swappiness=cfg.get("swappiness"))
    except SupervisorError as e:
        out["reason"] = str(e)
        return jsonify(out)
    try:
        issues = _supervisor("GET", "/resolution/info").get("issues") or []
        out["reboot_required"] = any(i.get("type") == "reboot_required" for i in issues)
    except SupervisorError:
        pass
    return jsonify(out)


@app.route("/api/swap/config", methods=["POST"])
def swap_config_set():
    denied = _write_guard()
    if denied:
        return denied
    body = request.get_json(silent=True) or {}
    payload = {}
    if "swap_size" in body:
        size_txt = str(body.get("swap_size") or "").strip().upper()
        try:
            size = parse_swap_size(size_txt)
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        if size is None:
            return jsonify({"error": "Size missing"}), 400
        try:
            free = psutil.disk_usage("/data").free
        except OSError:
            free = 0
        limit = min(SWAP_MAX_BYTES, max(0, free - SWAP_MIN_FREE_AFTER)) if free else SWAP_MAX_BYTES
        if size > limit:
            return jsonify({"error": f"Too large: at most {limit // 1024 ** 2} MB fits "
                                     f"(16 GB cap, {SWAP_MIN_FREE_AFTER // 1024 ** 3} GB stay free on the data disk)"}), 400
        payload["swap_size"] = size_txt
    if "swappiness" in body:
        try:
            sw = int(body.get("swappiness"))
        except (TypeError, ValueError):
            return jsonify({"error": "Swappiness must be a whole number"}), 400
        if not 0 <= sw <= 100:
            return jsonify({"error": "Swappiness must be between 0 and 100"}), 400
        payload["swappiness"] = sw
    if not payload:
        return jsonify({"error": "Nothing to change"}), 400
    try:
        before = _supervisor("GET", "/os/config/swap")
        _supervisor("POST", "/os/config/swap", payload)
    except SupervisorError as e:
        return jsonify({"error": str(e)}), e.status
    size_changed = "swap_size" in payload and str(before.get("swap_size") or "") != payload["swap_size"]
    print(f"[hardware-monitor] swap config set: {payload}", flush=True)
    return jsonify({"ok": True, "reboot_required": size_changed})


@app.route("/api/host/reboot", methods=["POST"])
def host_reboot():
    denied = _write_guard()
    if denied:
        return denied
    if (request.get_json(silent=True) or {}).get("confirm") != "reboot":
        return jsonify({"error": "Confirmation missing"}), 400
    print("[hardware-monitor] host reboot requested from the UI", flush=True)
    try:
        _supervisor("POST", "/host/reboot", {}, timeout=30)
    except SupervisorError as e:
        return jsonify({"error": str(e)}), e.status
    return jsonify({"ok": True})


def _install_safe_getfqdn():
    """Keep the reverse DNS lookup during bind from killing the addon.

    http.server calls socket.getfqdn() while binding. With host_network the
    addon uses the router's DNS; a PTR record that is not valid UTF-8 then
    raises UnicodeDecodeError and the addon never starts.
    """
    real_getfqdn = socket.getfqdn

    def safe_getfqdn(name=""):
        try:
            return real_getfqdn(name)
        except (UnicodeDecodeError, UnicodeError, OSError):
            return name or "localhost"

    socket.getfqdn = safe_getfqdn


if __name__ == "__main__":
    _install_safe_getfqdn()
    port = int(os.environ.get("PORT", 8200))
    app.run(host="0.0.0.0", port=port, debug=False)
