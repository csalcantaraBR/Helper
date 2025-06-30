# helper-installer

A small GUI application to display AIChain user info, GPU details and server heartbeat.

## Requirements
- Python 3.12
- See `requirements.txt`

## Installation
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Running
```bash
python main.py
```
On first launch, enter your API key. The key is stored in `~/.aichain_config.json` with `0600` permissions.

## Tests
```bash
pytest
```

## Build with PyInstaller
Install PyInstaller and run one of the following commands:

### Linux
```bash
pyinstaller --onefile --name helper-installer main.py
```

### macOS
```bash
pyinstaller --onefile --name helper-installer main.py
```

### Windows
```cmd
pyinstaller --onefile --name helper-installer.exe main.py
```

The executable will be in the `dist/` directory.

## Docker
Example image that runs the app:
```Dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["python", "main.py"]
```
