# ScanScribe Client - Build to EXE

## Development Setup

### Install Dependencies
```bash
pip install -r requirements.txt
pip install pyinstaller
```

### Run Locally
```bash
python scanscribe_client.py
```

## Build Windows EXE

### One-File Executable (Recommended)
```bash
pyinstaller --onefile --windowed --name "ScanScribe-Client" --icon=icon.ico scanscribe_client.py
```

### Output
- EXE will be in `dist/ScanScribe-Client.exe`
- Distribute to users (no Python required)

## Build Options

### With Icon (Recommended)
```bash
pyinstaller --onefile --windowed --name "ScanScribe-Client" --icon=icon.ico scanscribe_client.py
```

### With Console (Debug Mode)
```bash
pyinstaller --onefile --name "ScanScribe-Client" scanscribe_client.py
```

### Advanced Options
```bash
pyinstaller \
  --onefile \
  --windowed \
  --name "ScanScribe-Client" \
  --icon=icon.ico \
  --add-data "config.json;." \
  --hidden-import=requests \
  --hidden-import=watchdog \
  scanscribe_client.py
```

## Distribution

### Give users:
1. `ScanScribe-Client.exe`
2. Quick start guide:
   - Run EXE
   - Enter server IP (http://192.168.10.120:8000)
   - Login with credentials
   - Choose watch folder
   - Click "Start Watching"

### User Workflow
```
1. Download ScanScribe-Client.exe
2. Double-click to run
3. Login to ScanScribe server
4. Select folder (or use default)
5. Start watching
6. Recording software saves to that folder
7. Files auto-upload to ScanScribe
```

## Features
- ✅ Auto-reconnect on network issues
- ✅ Retry failed uploads
- ✅ System tray support (minimize to tray)
- ✅ Activity log
- ✅ Upload statistics
- ✅ No Python required for end users

## Future Enhancements
- Windows service mode (run in background)
- Auto-start on Windows login
- Bulk upload existing files
- Upload queue visualization
- Network bandwidth limiting
