import json
from unittest import mock
import sys
import types

import requests
import requests_mock

import main


def test_fetch_user_info():
    with requests_mock.Mocker() as m:
        m.get("https://api.aichain.io/v1/me", json={"name": "tester"})
        data = main.fetch_user_info("key")
        assert data["name"] == "tester"


def test_fetch_heartbeat():
    with requests_mock.Mocker() as m:
        m.get("https://api.aichain.io/v1/heartbeat", json={"ok": True})
        data = main.fetch_heartbeat("key")
        assert data["ok"] is True
        assert "latency_ms" in data


def test_get_gpu_info():
    fake_gpu = mock.Mock()
    fake_gpu.name = "GPU"
    fake_gpu.memoryTotal = 1000
    fake_gpu.memoryFree = 900
    fake_gpu.load = 0.5
    fake_mod = types.SimpleNamespace(getGPUs=lambda: [fake_gpu])
    sys.modules["GPUtil"] = fake_mod
    data = main.get_gpu_info()
    assert data[0]["name"] == "GPU"
    assert data[0]["memory_total"] == 1000


