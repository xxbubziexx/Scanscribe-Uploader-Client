# ScanScribe Client - Build on Linux for Windows

## Quick Build with Wine

### Automated Build (Recommended)
```bash
cd /home/scanscribe/Desktop/projects/scanscribe/client
./build-wine.sh
```

The script will:
1. ✅ Install Wine (if needed)
2. ✅ Download & install Python for Windows in Wine
3. ✅ Install dependencies
4. ✅ Build Windows EXE

**Output:** `dist/ScanScribe-Client.exe` (~15-20MB)

---

## Manual Build Steps

### 1. Install Wine
```bash
sudo dpkg --add-architecture i386
sudo apt update
sudo apt install -y wine64 wine32
```

### 2. Download Python for Windows
```bash
cd /tmp
wget https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe
```

### 3. Install Python in Wine
```bash
wine python-3.11.9-amd64.exe /quiet InstallAllUsers=1 PrependPath=1
```

### 4. Install Dependencies
```bash
cd /home/scanscribe/Desktop/projects/scanscribe/client
wine python -m pip install --upgrade pip
wine python -m pip install -r requirements.txt
wine python -m pip install pyinstaller
```

### 5. Build EXE
```bash
wine pyinstaller --onefile --windowed --name "ScanScribe-Client" scanscribe_client.py
```

### 6. Output
```
dist/ScanScribe-Client.exe  ← Distribute this file
```

---

## Test the EXE (Optional)

### On Linux with Wine
```bash
wine dist/ScanScribe-Client.exe
```

### On Windows VM/Machine
Copy `dist/ScanScribe-Client.exe` to Windows and double-click.

---

## Troubleshooting

### Wine Python not found
```bash
# Find Wine Python path
find ~/.wine -name python.exe

# Use full path
wine "C:\\Python311\\python.exe" --version
```

### PyInstaller fails
```bash
# Try without --windowed (shows console for debugging)
wine pyinstaller --onefile --name "ScanScribe-Client" scanscribe_client.py
```

### Missing dependencies
```bash
wine python -m pip install --force-reinstall requests watchdog
```

---

## Notes

- **First build takes ~5-10 minutes** (Wine + Python install)
- **Subsequent builds take ~1-2 minutes**
- **EXE size:** ~15-20MB (includes Python runtime)
- **No Python required on end-user Windows machines**
- **Works on Windows 7/8/10/11**

---

## Alternative: Docker Build Container

If Wine is problematic, use Docker with Windows build container:

```bash
docker run -v "$PWD:/src" cdrx/pyinstaller-windows:python3 \
  "pyinstaller --onefile --windowed --name ScanScribe-Client scanscribe_client.py"
```
