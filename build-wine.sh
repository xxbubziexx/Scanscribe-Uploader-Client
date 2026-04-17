#!/bin/bash
# Build ScanScribe Client for Windows using Wine on Linux

set -e

echo "🍷 Building ScanScribe Client for Windows using Wine..."

# Check if Wine is installed
if ! command -v wine &> /dev/null; then
    echo "❌ Wine not found. Installing..."
    sudo dpkg --add-architecture i386
    sudo apt update
    sudo apt install -y wine64 wine32
fi

# Check if Python for Windows is installed in Wine
if ! wine python --version &> /dev/null; then
    echo "📥 Downloading Python for Windows..."
    cd /tmp
    wget -q https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe
    
    echo "⚙️ Installing Python in Wine (this may take a few minutes)..."
    wine python-3.11.9-amd64.exe /quiet InstallAllUsers=1 PrependPath=1
    
    echo "✅ Python installed in Wine"
fi

# Navigate to client directory
cd "$(dirname "$0")"

# Install dependencies
echo "📦 Installing Python dependencies..."
wine python -m pip install --upgrade pip
wine python -m pip install -r requirements.txt
wine python -m pip install pyinstaller

# Clean previous builds
echo "🧹 Cleaning previous builds..."
rm -rf build dist __pycache__

# Build EXE (uses committed PyInstaller spec)
echo "🔨 Building Windows EXE..."
wine pyinstaller ScanScribe-Client.spec

# Check if build succeeded
if [ -f "dist/ScanScribe-Client.exe" ]; then
    echo ""
    echo "✅ BUILD SUCCESSFUL!"
    echo "📦 Output: dist/ScanScribe-Client.exe"
    echo "📊 Size: $(du -h dist/ScanScribe-Client.exe | cut -f1)"
    echo ""
    echo "🚀 Ready to distribute to Windows users!"
else
    echo "❌ Build failed"
    exit 1
fi
