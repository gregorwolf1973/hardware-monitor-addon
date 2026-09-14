#!/usr/bin/env python3
"""Swap configuration: recommendation, validation, ingress-only writes, Supervisor calls."""
import os
import sys
import unittest
from collections import namedtuple
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "app"))

import app as hm  # noqa: E402

GIB = 1024 ** 3
INGRESS = {"REMOTE_ADDR": "172.30.32.2"}
HDR = {"X-HM-Action": "1"}
Mem = namedtuple("Mem", "total available percent used")
Swap = namedtuple("Swap", "total used percent")
Disk = namedtuple("Disk", "total used free percent")


class RecommendationTest(unittest.TestCase):
    def test_four_gb_ram_on_ssd(self):
        size, swappiness, reasons = hm.recommend_swap(int(3.8 * GIB), 0, 100 * GIB, "ssd")
        self.assertEqual((size, swappiness), ("4G", 1))
        self.assertTrue(reasons)

    def test_other_sizes(self):
        self.assertEqual(hm.recommend_swap(2 * GIB, 0, 100 * GIB, "ssd")[0], "2G")
        self.assertEqual(hm.recommend_swap(8 * GIB, 0, 100 * GIB, "ssd")[0], "4G")
        self.assertEqual(hm.recommend_swap(32 * GIB, 0, 100 * GIB, "ssd")[0], "8G", "gedeckelt")

    def test_heavy_swap_use_and_limits(self):
        self.assertEqual(hm.recommend_swap(4 * GIB, int(2.6 * GIB), 100 * GIB, "ssd")[0], "6G")
        self.assertEqual(hm.recommend_swap(4 * GIB, 0, 100 * GIB, "sd")[0], "2G", "SD-Karte klein halten")
        self.assertEqual(hm.recommend_swap(4 * GIB, 0, 5 * GIB, "ssd")[0], "2G", "freier Platz begrenzt")
        self.assertEqual(hm.recommend_swap(int(15.4 * GIB), 0, 100 * GIB, "ssd")[0], "8G", "auf Stufe gerundet, nicht 7G")
        self.assertEqual(hm.recommend_swap(4 * GIB, int(1.6 * GIB), 100 * GIB, "ssd")[0], "4G")
        self.assertEqual(hm.recommend_swap(4 * GIB, 0, 1 * GIB, "ssd")[0], "0")

    def test_parse(self):
        self.assertEqual(hm.parse_swap_size("4G"), 4 * GIB)
        self.assertEqual(hm.parse_swap_size("512m"), 512 * 1024 ** 2)
        self.assertIsNone(hm.parse_swap_size(""))
        for bad in ("4 GB", "-1G", "4T", "abc", "1.5G"):
            with self.assertRaises(ValueError, msg=bad):
                hm.parse_swap_size(bad)


class ApiTest(unittest.TestCase):
    def setUp(self):
        self.c = hm.app.test_client()
        self.calls = []
        self.state = {"swap_size": "2G", "swappiness": 1}
        self.issues = []

        def fake(method, path, payload=None, timeout=15):
            self.calls.append((method, path, payload))
            if path == "/os/config/swap" and method == "GET":
                return dict(self.state)
            if path == "/os/config/swap" and method == "POST":
                self.state.update(payload)
                return {}
            if path == "/resolution/info":
                return {"issues": self.issues}
            if path == "/host/reboot":
                return {}
            raise AssertionError(path)
        patches = [
            mock.patch.object(hm, "_supervisor", side_effect=fake),
            mock.patch.object(hm.psutil, "virtual_memory", return_value=Mem(4 * GIB, 2 * GIB, 50.0, 2 * GIB)),
            mock.patch.object(hm.psutil, "swap_memory", return_value=Swap(2 * GIB, GIB // 2, 25.0)),
            mock.patch.object(hm.psutil, "disk_usage", return_value=Disk(100 * GIB, 60 * GIB, 40 * GIB, 60.0)),
            mock.patch.object(hm, "_data_storage_kind", return_value="ssd"),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def test_get_reports_config_and_recommendation(self):
        d = self.c.get("/api/swap/config", environ_base=INGRESS).get_json()
        self.assertTrue(d["available"])
        self.assertEqual((d["swap_size"], d["swappiness"]), ("2G", 1))
        self.assertEqual(d["recommended"]["swap_size"], "4G")
        self.assertTrue(d["can_change"])
        self.assertFalse(d["reboot_required"])
        self.assertEqual(d["max_bytes"], 16 * GIB)
        self.issues.append({"type": "reboot_required"})
        self.assertTrue(self.c.get("/api/swap/config").get_json()["reboot_required"])

    def test_lan_access_can_read_but_not_change(self):
        lan = {"REMOTE_ADDR": "192.168.178.50"}
        self.assertFalse(self.c.get("/api/swap/config", environ_base=lan).get_json()["can_change"])
        r = self.c.post("/api/swap/config", json={"swap_size": "4G"}, headers=HDR, environ_base=lan)
        self.assertEqual(r.status_code, 403)
        r = self.c.post("/api/host/reboot", json={"confirm": "reboot"}, headers=HDR, environ_base=lan)
        self.assertEqual(r.status_code, 403)
        self.assertNotIn(("POST", "/os/config/swap", {"swap_size": "4G"}), self.calls)
        self.assertNotIn("/host/reboot", [c[1] for c in self.calls])

    def test_write_needs_json_and_header(self):
        r = self.c.post("/api/swap/config", data="swap_size=4G", environ_base=INGRESS,
                        content_type="application/x-www-form-urlencoded")
        self.assertEqual(r.status_code, 400)
        r = self.c.post("/api/swap/config", json={"swap_size": "4G"}, environ_base=INGRESS)
        self.assertEqual(r.status_code, 400, "ohne eigenen Header")

    def test_set_size_and_swappiness(self):
        r = self.c.post("/api/swap/config", json={"swap_size": "4g", "swappiness": 10}, headers=HDR, environ_base=INGRESS)
        self.assertEqual(r.status_code, 200, r.get_json())
        self.assertTrue(r.get_json()["reboot_required"])
        self.assertEqual(self.state, {"swap_size": "4G", "swappiness": 10})
        r = self.c.post("/api/swap/config", json={"swappiness": 5}, headers=HDR, environ_base=INGRESS)
        self.assertFalse(r.get_json()["reboot_required"], "nur Swappiness braucht keinen Neustart")

    def test_validation(self):
        for body in ({"swap_size": "4 GB"}, {"swap_size": "20G"}, {"swappiness": 150}, {"swappiness": "x"}, {}):
            r = self.c.post("/api/swap/config", json=body, headers=HDR, environ_base=INGRESS)
            self.assertEqual(r.status_code, 400, body)
        with mock.patch.object(hm.psutil, "disk_usage", return_value=Disk(10 * GIB, 7 * GIB, 3 * GIB, 70.0)):
            r = self.c.post("/api/swap/config", json={"swap_size": "2G"}, headers=HDR, environ_base=INGRESS)
            self.assertEqual(r.status_code, 400, "passt nicht mehr auf die Datenpartition")
        self.assertEqual(self.state["swap_size"], "2G")

    def test_reboot_needs_confirmation(self):
        r = self.c.post("/api/host/reboot", json={}, headers=HDR, environ_base=INGRESS)
        self.assertEqual(r.status_code, 400)
        r = self.c.post("/api/host/reboot", json={"confirm": "reboot"}, headers=HDR, environ_base=INGRESS)
        self.assertEqual(r.status_code, 200)
        self.assertIn(("POST", "/host/reboot", {}), self.calls)

    def test_old_os_is_reported(self):
        def old(method, path, payload=None, timeout=15):
            raise hm.SupervisorError("Home Assistant OS 15.0 or newer required for swap settings", 404)
        with mock.patch.object(hm, "_supervisor", side_effect=old):
            d = self.c.get("/api/swap/config", environ_base=INGRESS).get_json()
        self.assertFalse(d["available"])
        self.assertIn("15.0", d["reason"])


class SupervisorClientTest(unittest.TestCase):
    def test_missing_token(self):
        with mock.patch.dict(os.environ, {"SUPERVISOR_TOKEN": ""}):
            with self.assertRaises(hm.SupervisorError):
                hm._supervisor("GET", "/os/config/swap")


if __name__ == "__main__":
    unittest.main()
