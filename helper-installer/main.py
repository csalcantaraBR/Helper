import json
import os
import time
import requests
import PySimpleGUI as sg

CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".aichain_config.json")
TIMEOUT = 5


def load_api_key():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH) as f:
                data = json.load(f)
            return data.get("api_key")
        except Exception:
            return None
    return None


def save_api_key(key: str):
    with open(CONFIG_PATH, "w") as f:
        json.dump({"api_key": key}, f)
    os.chmod(CONFIG_PATH, 0o600)


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


def main():
    api_key = load_api_key()

    sg.theme("SystemDefault")

    if not api_key:
        layout = [
            [sg.Text("Enter API Key")],
            [sg.Input(password_char="*", key="-API-")],
            [sg.Button("Save")],
        ]
        window = sg.Window("helper-installer", layout)
        while True:
            event, values = window.read()
            if event == sg.WINDOW_CLOSED:
                window.close()
                return
            if event == "Save":
                api_key = values.get("-API-")
                if api_key:
                    save_api_key(api_key)
                    break
                else:
                    sg.popup_error("API key required")
        window.close()

    try:
        profile = fetch_user_info(api_key)
    except Exception as e:
        profile = {"error": str(e)}
        sg.popup_error(f"Failed to load profile: {e}")
    try:
        hb = fetch_heartbeat(api_key)
    except Exception as e:
        hb = {"error": str(e)}
        sg.popup_error(f"Failed to load heartbeat: {e}")
    gpu_info = get_gpu_info()

    layout = [
        [sg.Text("User Profile")],
        [sg.Multiline(json.dumps(profile, indent=2), size=(60, 10), key="-PROFILE-")],
        [sg.Text("GPU Info")],
        [sg.Multiline(json.dumps(gpu_info, indent=2), size=(60, 5), key="-GPU-")],
        [sg.Text("Heartbeat")],
        [sg.Multiline(json.dumps(hb, indent=2), size=(60, 5), key="-HB-")],
        [sg.Button("Refresh Heartbeat"), sg.Button("Exit")],
    ]

    window = sg.Window("helper-installer", layout)
    while True:
        event, _ = window.read()
        if event in (sg.WINDOW_CLOSED, "Exit"):
            break
        if event == "Refresh Heartbeat":
            try:
                hb = fetch_heartbeat(api_key)
                window["-HB-"].update(json.dumps(hb, indent=2))
            except Exception as e:
                sg.popup_error(f"Failed to refresh heartbeat: {e}")
    window.close()


if __name__ == "__main__":
    main()
