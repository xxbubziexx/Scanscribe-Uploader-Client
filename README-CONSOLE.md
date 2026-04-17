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

### Interactive Setup
```bash
python scanscribe_client_console.py --setup
```
Prompts for:
- Server URL
- Username
- Password
- Watch folder

### Command Line Arguments
```bash
python scanscribe_client_console.py \
  --server http://192.168.10.120:8000 \
  --username john \
  --password secret123 \
  --folder "C:\Audio\Recordings"
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

### First Time
```cmd
ScanScribe-Client.exe --setup
```

### Normal Operation
```cmd
ScanScribe-Client.exe
```

### With Arguments
```cmd
ScanScribe-Client.exe --server http://192.168.10.120:8000 -u john -p secret123
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
