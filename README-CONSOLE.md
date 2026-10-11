# ScanScribe Client - Console Version

## Quick Start

### First Time Setup
```bash
python scanscribe_client_console.py --setup
```

### Start Watching
```bash
python scanscribe_client_console.py
```

---

## Usage

### Interactive Setup Wizard
```bash
python scanscribe_client_console.py --setup
```
Prompts for:
- Server URL (e.g., `http://192.168.1.100:8000`)
- Username
- Password (validates live with server)
- Local scanner watch folder (e.g., `C:\ProScan\Recordings` or `C:\SDRTrunk\recordings`)
- Automatic file deletion toggle

### Test Server Connection & Pipeline
```bash
python scanscribe_client_console.py --test
```
Performs a fast end-to-end diagnostic:
- Tests network latency & reachability to the ScanScribe server
- Validates configured credentials
- Queries `/api/upload/status` to confirm the upload pipeline is online, displays remote ingest directory, and lists allowed audio formats

### Command Line Arguments
```bash
python scanscribe_client_console.py \
  --server http://192.168.1.100:8000 \
  --username admin \
  --password secret123 \
  --folder "C:\ProScan\Recordings"
```

### Headless / Background Operation (Non-Interactive)
```bash
python scanscribe_client_console.py --no-interactive
```

### Using Config File
```bash
# Custom config location
python scanscribe_client_console.py --config my-config.json
```

---

## Build EXE

### Basic Build
```bash
wine python -m pip install pyyaml==6.0.2
wine pyinstaller --onefile --name "ScanScribe-Client" scanscribe_client_console.py
```

### Output
```
dist/ScanScribe-Client.exe
```

---

## Running the EXE

### First Time Setup Wizard
```cmd
ScanScribe-Client.exe --setup
```

### Test Connection
```cmd
ScanScribe-Client.exe --test
```

### Normal Operation
```cmd
ScanScribe-Client.exe
```

### With Arguments
```cmd
ScanScribe-Client.exe --server http://192.168.1.100:8000 -u admin -p secret123
```

---

## Features

✅ **Lightweight** - No GUI overhead  
✅ **Colored console output** - Easy to read logs  
✅ **Stability monitoring** - Waits for files to finish  
✅ **Auto-reconnect** - Handles network issues  
✅ **Statistics** - Shows upload/fail counts  
✅ **Configurable** - CLI args or config file  
✅ **Cross-platform** - Windows/Linux/Mac  

---

## Console Output

```
╔═══════════════════════════════════════╗
║     ScanScribe Client v1.0            ║
╚═══════════════════════════════════════╝

[12:34:56] 🔐 Authenticating as john...
[12:34:57] ✅ Connected to http://192.168.10.120:8000
[12:34:57] 👁️  Watching: C:\Audio\Recordings
[12:34:57] ✅ Watcher started
[12:35:10] 📊 Monitoring: test.wav (stability: 5.0s)
[12:35:12] 📈 Growing: test.wav (12,345 bytes)
[12:35:15] 📤 Uploading: test.wav (1.23 MB)
[12:35:16] ✅ test.wav uploaded successfully

📊 Statistics:
  Uploaded: 1
  Failed:   0
  Total:    1.23 MB
```

---

## Run as Windows Service

### Using NSSM (Non-Sucking Service Manager)
```cmd
nssm install ScanScribe "C:\Path\To\ScanScribe-Client.exe"
nssm start ScanScribe
```

---

## Comparison: GUI vs Console

| Feature | GUI | Console |
|---------|-----|---------|
| Size | ~20MB | ~15MB |
| Memory | ~80MB | ~30MB |
| Background | ❌ | ✅ |
| Windows Service | ❌ | ✅ |
| Remote Use | ❌ | ✅ (SSH) |
| Easy to Monitor | ✅ | ✅ |
| Auto-start | Manual | Easy |

**Console = Better for production! 🎯**
