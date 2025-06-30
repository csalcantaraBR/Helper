import json
import os
import queue
import sys
import threading
import types
from unittest import mock

import requests_mock

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import main


def test_fetch_user_info():
    with requests_mock.Mocker() as m:
        m.get("https://api.aichain.io/v1/me", json={"name": "tester"})
        data = main.fetch_user_info("key")
        assert data["name"] == "tester"


def test_heartbeat_loop_post(monkeypatch):
    class Stopper:
        def __init__(self):
            self.called = False

        def is_set(self):
            return self.called

        def wait(self, timeout):
            self.called = True
            return True

    with requests_mock.Mocker() as m:
        m.post(main.BASE_URL + main.HEARTBEAT_ENDPOINT, json={"ok": True})
        monkeypatch.setattr(main, "HEARTBEAT_INTERVAL", 0)
        monkeypatch.setattr(main, "get_gpu_info", lambda: [])
        q = queue.Queue()
        stopper = Stopper()
        main.heartbeat_loop("key", "wallet", q, stopper)
        assert m.called
        req = m.request_history[0]
        assert req.method == "POST"
        assert req.json() == {"wallet": "wallet", "gpu_count": 0}
        assert not q.empty()


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


def test_save_and_load_config(tmp_path, monkeypatch):
    cfg = tmp_path / "config.json"
    monkeypatch.setattr(main, "CONFIG_PATH", cfg)
    main.save_config("abc", "wallet1")
    assert cfg.exists()
    with open(cfg) as f:
        data = json.load(f)
    assert data == {"api_key": "abc", "wallet": "wallet1"}
    loaded = main.load_config()
    assert loaded == {"api_key": "abc", "wallet": "wallet1"}


