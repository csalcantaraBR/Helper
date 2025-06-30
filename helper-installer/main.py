import json
import os
import queue
import threading
import time
from typing import Dict

import requests
import PySimpleGUI as sg

BASE_URL = "https://us-central1-aichain-launchpad.cloudfunctions.net"
HEARTBEAT_ENDPOINT = "/heartbeat"
HEARTBEAT_INTERVAL = 300  # 5 minutes
TIMEOUT = 10
CONFIG_PATH = os.path.join(os.path.expanduser('~'), '.aichain_config.json')


def load_config() -> Dict[str, str]:
    """Load API key and wallet from CONFIG_PATH."""
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH) as f:
                data = json.load(f)
            return {
                "api_key": data.get("api_key", ""),
                "wallet": data.get("wallet", ""),
            }
        except Exception:
            return {"api_key": "", "wallet": ""}
    return {"api_key": "", "wallet": ""}


def save_config(api_key: str, wallet: str) -> None:
    """Persist API key and wallet to CONFIG_PATH with 0600 perms."""
    with open(CONFIG_PATH, "w") as f:
        json.dump({"api_key": api_key, "wallet": wallet}, f)
    os.chmod(CONFIG_PATH, 0o600)


# Backward compatible helpers
load_api_key = lambda: load_config().get("api_key")
save_api_key = lambda key: save_config(key, load_config().get("wallet", ""))


def fetch_user_info(api_key: str):
    headers = {"X-API-Key": api_key}
    resp = requests.get("https://api.aichain.io/v1/me", headers=headers, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def fetch_heartbeat(api_key: str):
    headers = {"X-API-Key": api_key}
    start = time.time()
    resp = requests.get("https://api.aichain.io/v1/heartbeat", headers=headers, timeout=TIMEOUT)
    latency_ms = int((time.time() - start) * 1000)
    resp.raise_for_status()
    data = resp.json()
    data["latency_ms"] = latency_ms
    return data


def get_gpu_info():
    gpus = []
    try:
        import GPUtil
        for gpu in GPUtil.getGPUs():
            gpus.append(
                {
                    "name": gpu.name,
                    "memory_total": gpu.memoryTotal,
                    "memory_free": gpu.memoryFree,
                    "load": gpu.load,
                }
            )
    except Exception:
        pass
    return gpus


def heartbeat_loop(api_key: str, wallet: str, log_q: queue.Queue, stop: threading.Event) -> None:
    """Send heartbeats periodically in a background thread."""
    url = BASE_URL + HEARTBEAT_ENDPOINT
    headers = {"Content-Type": "application/json", "X-API-Key": api_key}
    while not stop.is_set():
        gpus = get_gpu_info()
        gpu_desc = ", ".join(f"{g['name']} {g['memory_total']}MB" for g in gpus) or "no GPU"
        payload = {"wallet": wallet, "gpu_count": len(gpus)}
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=TIMEOUT)
            try:
                resp_json = resp.json()
            except Exception:
                resp_json = resp.text
            if resp.status_code == 200:
                msg = f"{ts} OK {resp.status_code}: {resp_json} GPUs: {gpu_desc}"
            elif resp.status_code in (400, 401, 403, 500):
                msg = f"{ts} Error {resp.status_code}: {resp_json}"
            else:
                msg = f"{ts} Status {resp.status_code}: {resp_json}"
        except requests.Timeout:
            msg = f"{ts} Timeout after {TIMEOUT}s"
        except Exception as e:
            msg = f"{ts} Failure: {e}"
        log_q.put(msg)
        if stop.wait(HEARTBEAT_INTERVAL):
            break


def main() -> None:
    cfg = load_config()

    sg.theme("SystemDefault")
    layout = [
        [sg.Text("API Key"), sg.Input(default_text=cfg.get("api_key"), key="-API-", password_char="*")],
        [sg.Text("Wallet"), sg.Input(default_text=cfg.get("wallet"), key="-WALLET-")],
        [sg.Button("Save & Start Heartbeat")],
        [sg.Multiline(size=(80, 20), key="-LOG-", autoscroll=True)],
    ]
    window = sg.Window("helper-installer", layout)
    log_q: queue.Queue[str] = queue.Queue()
    stop_event = threading.Event()
    thread = None

    while True:
        event, values = window.read(timeout=100)
        if event == sg.WINDOW_CLOSED:
            stop_event.set()
            break
        if event == "Save & Start Heartbeat":
            api_key = values.get("-API-")
            wallet = values.get("-WALLET-")
            if not api_key or not wallet:
                sg.popup_error("API key and wallet required")
                continue
            save_config(api_key, wallet)
            if thread is None or not thread.is_alive():
                stop_event.clear()
                thread = threading.Thread(
                    target=heartbeat_loop,
                    args=(api_key, wallet, log_q, stop_event),
                    daemon=True,
                )
                thread.start()
        while not log_q.empty():
            msg = log_q.get()
            window["-LOG-"].update(msg + "\n", append=True)
    window.close()


if __name__ == "__main__":
    main()
