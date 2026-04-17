#!/usr/bin/env python3
"""
ScanScribe Client - Console Version
Watches a local folder and uploads audio files to ScanScribe server
"""
import os
import sys
import time
import json
import signal
import argparse
from pathlib import Path
from datetime import datetime
import requests
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

try:
    import yaml
except ImportError:
    yaml = None

# Audio metadata for duration rejection
try:
    import mutagen
    MUTAGEN_AVAILABLE = True
except ImportError:
    mutagen = None
    MUTAGEN_AVAILABLE = False

# Enable ANSI colors on Windows
try:
    import colorama
    colorama.init()
except ImportError:
    # colorama not installed, try Windows-specific fix
    if sys.platform == 'win32':
        # Enable ANSI escape sequences on Windows 10+
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        except:
            pass

# ANSI color codes
class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    CYAN = '\033[36m'
    GRAY = '\033[90m'

# Default configuration
DEFAULT_CONFIG = {
    "server_url": "http://192.168.10.120:8000",
    "username": "",
    "password": "",
    "watch_folder": str(Path.home() / "ScanScribe-Ingest"),
    "extensions": [".wav", ".mp3"],
    "auto_start": True,
    "delete_after_upload": True  # Delete local file after successful upload
}

CONFIG_FILE = Path.home() / ".scanscribe-client.json"


class ScanScribeClient:
    """Main client application."""
    
    def __init__(self, config_path=CONFIG_FILE):
        self.config_path = config_path
        self.config = self.load_config()
        self.token = None
        self.observer = None
        self.running = False
        self.stats = {
            "uploaded": 0,
            "failed": 0,
            "rejected": 0,
            "total_mb": 0.0
        }
        
    def load_config(self):
        """Load configuration from file."""
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                return json.load(f)
        return DEFAULT_CONFIG.copy()
    
    def save_config(self):
        """Save configuration to file."""
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=2)
        print(f"{Colors.GRAY}📝 Config saved to {self.config_path}{Colors.RESET}")
    
    def log(self, message, level="info"):
        """Print colored log message."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        if level == "success":
            color = Colors.GREEN
        elif level == "error":
            color = Colors.RED
        elif level == "warning":
            color = Colors.YELLOW
        elif level == "info":
            color = Colors.CYAN
        else:
            color = Colors.RESET
        
        print(f"{Colors.GRAY}[{timestamp}]{Colors.RESET} {color}{message}{Colors.RESET}")
    
    def login(self, username=None, password=None, silent=False):
        """Authenticate with ScanScribe server."""
        username = username or self.config.get("username")
        password = password or self.config.get("password")
        
        if not username or not password:
            if not silent:
                self.log("❌ Username and password required", "error")
            return False
        
        try:
            if not silent:
                self.log(f"🔐 Authenticating as {username}...", "info")
            
            response = requests.post(
                f"{self.config['server_url']}/api/auth/login",
                data={"username": username, "password": password},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.token = data["access_token"]
                self.config["username"] = username
                if not silent:
                    self.log(f"✅ Connected to {self.config['server_url']}", "success")
                return True
            else:
                error = response.json().get("detail", "Login failed")
                if not silent:
                    self.log(f"❌ {error}", "error")
                return False
                
        except Exception as e:
            if not silent:
                self.log(f"❌ Connection error: {str(e)}", "error")
            return False
    
    def auto_relogin(self):
        """Automatically re-login using saved credentials."""
        username = self.config.get("username")
        password = self.config.get("password")
        
        if not username or not password:
            self.log("⚠️  Cannot auto-relogin: no saved credentials", "warning")
            return False
        
        self.log("🔄 Token expired, re-authenticating...", "warning")
        
        for attempt in range(3):
            if self.login(username, password, silent=True):
                self.log("✅ Re-authenticated successfully", "success")
                return True
            time.sleep(2 ** attempt)  # Exponential backoff: 1s, 2s, 4s
        
        self.log("❌ Auto-relogin failed after 3 attempts", "error")
        return False

    def report_rejected(self, count: int = 1, retry_on_auth: bool = True) -> bool:
        """Report rejected file(s) to server for dashboard stats (best-effort)."""
        if not self.token:
            return False
        if count <= 0:
            return True

        try:
            resp = requests.post(
                f"{self.config['server_url']}/api/watcher/rejected",
                json={"count": int(count)},
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=5,
            )

            # Handle token expiration
            if resp.status_code == 401 and retry_on_auth:
                if self.auto_relogin():
                    return self.report_rejected(count=count, retry_on_auth=False)
                return False

            return resp.status_code == 200
        except Exception:
            # Do not crash client if server is unreachable
            return False
    
    def fetch_server_config(self, retry_on_auth=True):
        """Fetch watchdog_client settings from server."""
        try:
            response = requests.get(
                f"{self.config['server_url']}/api/settings/config",
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=5
            )
            
            # Handle token expiration
            if response.status_code == 401 and retry_on_auth:
                if self.auto_relogin():
                    return self.fetch_server_config(retry_on_auth=False)
            
            if response.status_code == 200 and yaml:
                # Server returns JSON: {"content": "<yaml>"} (settings API)
                yaml_text = None
                try:
                    data = response.json()
                    if isinstance(data, dict) and isinstance(data.get("content"), str):
                        yaml_text = data["content"]
                except Exception:
                    # Not JSON, may already be raw YAML
                    yaml_text = None

                if yaml_text is None:
                    yaml_text = response.text

                config = yaml.safe_load(yaml_text) or {}
                # Back-compat: if YAML parser produced {"content": "<yaml>"} then parse inner
                if isinstance(config, dict) and isinstance(config.get("content"), str):
                    config = yaml.safe_load(config["content"]) or {}
                
                # Get watchdog_client settings (new structure)
                watchdog = config.get('watchdog_client', {})
                stability = watchdog.get('stability', {})
                rejection = watchdog.get('rejection', {})
                size_rejection = rejection.get('size', {})
                duration_rejection = rejection.get('duration', {})
                
                server_config = {
                    # Stability settings
                    'filesize_check_ms': stability.get('filesize_check_ms', 600),
                    'stability_window_ms': stability.get('stability_window_ms', 800),
                    # Rejection settings
                    'reject_size_enabled': size_rejection.get('enabled', False),
                    'reject_size_min_kb': size_rejection.get('min_kb', 100),
                    'reject_duration_enabled': duration_rejection.get('enabled', True),
                    'reject_duration_min_seconds': duration_rejection.get('min_seconds', 2.5),
                    # Extensions
                    'extensions': watchdog.get('extensions', ['.wav', '.mp3']),
                    # Delete after upload
                    'delete_after_upload': watchdog.get('delete_after_upload', True)
                }

                # Apply server-provided runtime settings immediately (no need to edit local config)
                # Extensions are used by the event handler/filtering logic.
                self.config["extensions"] = server_config["extensions"]
                # delete_after_upload is consumed from server_config in handler; keep local toggle as UI display only.
                
                # Log settings
                self.log(f"📋 Server config loaded (watchdog_client)", "info")
                self.log(f"   Stability: {server_config['filesize_check_ms']}ms check, {server_config['stability_window_ms']}ms window", "info")
                if server_config['reject_size_enabled']:
                    self.log(f"   Size filter: ON (min {server_config['reject_size_min_kb']} KB)", "info")
                else:
                    self.log(f"   Size filter: OFF", "info")
                if server_config['reject_duration_enabled']:
                    self.log(f"   Duration filter: ON (min {server_config['reject_duration_min_seconds']}s)", "info")
                else:
                    self.log(f"   Duration filter: OFF", "info")
                self.log(f"   Extensions: {', '.join(server_config['extensions'])}", "info")
                self.log(f"   Delete after upload: {'ON' if server_config['delete_after_upload'] else 'OFF'}", "info")
                
                return server_config
        except Exception as e:
            self.log(f"⚠️  Could not fetch server config: {str(e)}", "warning")
        
        # Fallback defaults
        self.log("📋 Using default config (server unreachable)", "warning")
        return {
            'filesize_check_ms': 600,
            'stability_window_ms': 800,
            'reject_size_enabled': False,
            'reject_size_min_kb': 100,
            'reject_duration_enabled': True,
            'reject_duration_min_seconds': 2.5,
            'extensions': ['.wav', '.mp3'],
            'delete_after_upload': True
        }
    
    def check_rejection(self, file_path, server_config):
        """
        Check if file should be rejected based on server config.
        Returns rejection reason string, or None if file passes.
        """
        file_size = file_path.stat().st_size
        
        # Size-based rejection
        if server_config.get('reject_size_enabled', False):
            min_kb = server_config.get('reject_size_min_kb', 100)
            if min_kb > 0:
                file_size_kb = file_size // 1024
                if file_size_kb < min_kb:
                    return f"size {file_size_kb}KB < {min_kb}KB min"
        
        # Duration-based rejection
        if server_config.get('reject_duration_enabled', False):
            min_seconds = server_config.get('reject_duration_min_seconds', 2.5)
            if min_seconds > 0:
                duration = self._get_audio_duration(file_path)
                if duration > 0 and duration < min_seconds:
                    return f"duration {duration:.1f}s < {min_seconds:.1f}s min"
        
        return None
    
    def _get_audio_duration(self, file_path):
        """Get audio duration using mutagen (fast metadata read)."""
        if not MUTAGEN_AVAILABLE:
            self.log("⚠️  mutagen not installed - duration rejection disabled", "warning")
            return 0.0
        
        try:
            audio = mutagen.File(str(file_path))
            if audio and hasattr(audio.info, 'length'):
                return float(audio.info.length)
            else:
                self.log(f"⚠️  Could not read duration: {file_path.name}", "warning")
        except Exception as e:
            self.log(f"⚠️  Duration read error: {str(e)}", "warning")
        return 0.0
    
    def upload_file(self, file_path, retry_on_auth=True):
        """Upload file to ScanScribe server."""
        try:
            with open(file_path, 'rb') as f:
                files = {'file': (Path(file_path).name, f, 'audio/wav')}
                
                response = requests.post(
                    f"{self.config['server_url']}/api/upload/audio",
                    files=files,
                    headers={"Authorization": f"Bearer {self.token}"},
                    timeout=120
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self.stats["uploaded"] += 1
                    self.stats["total_mb"] += data.get("size_mb", 0)
                    return True, data.get("message", "Upload successful")
                elif response.status_code == 401 and retry_on_auth:
                    # Token expired, try to re-login
                    if self.auto_relogin():
                        # Retry the upload once
                        return self.upload_file(file_path, retry_on_auth=False)
                    else:
                        self.stats["failed"] += 1
                        return False, "Authentication failed"
                else:
                    self.stats["failed"] += 1
                    return False, response.json().get("detail", "Upload failed")
                    
        except Exception as e:
            self.stats["failed"] += 1
            return False, f"Upload error: {str(e)}"
    
    def start_watching(self, prompt_existing=True):
        """Start watching the folder."""
        watch_path = Path(self.config["watch_folder"])
        watch_path.mkdir(parents=True, exist_ok=True)
        
        # Fetch server config
        server_config = self.fetch_server_config()
        
        # Check for existing files before starting watcher
        existing_files = self.get_existing_audio_files(watch_path)
        if existing_files and prompt_existing:
            self.log(f"📁 Found {len(existing_files)} existing file(s) in watch folder", "warning")
            for f in existing_files:
                self.log(f"   - {f.name}", "info")
            
            choice = input(f"\n{Colors.YELLOW}Upload these files now? (y/n):{Colors.RESET} ").strip().lower()
            
            if choice == 'y':
                self.log("📤 Processing existing files...", "info")
                
                # Create temporary handler for existing files
                temp_handler = AudioFileHandler(self, server_config)
                
                for file_path in existing_files:
                    temp_handler.process_existing(file_path)
                
                self.log("✅ Existing files processed", "success")
            else:
                self.log("⏭️  Skipped existing files", "info")
            
            print()  # Blank line
        
        self.log(f"👁️  Watching: {watch_path}", "info")
        
        # Create handler and store reference for periodic scanning
        self.handler = AudioFileHandler(self, server_config)
        self.watch_path = watch_path
        
        self.observer = Observer()
        self.observer.schedule(self.handler, str(watch_path), recursive=False)
        self.observer.start()
        self.running = True
        
        self.log("✅ Watcher started", "success")
        
        return True
    
    def scan_existing_files(self):
        """Scan watch folder for any unprocessed files."""
        if not hasattr(self, 'handler') or not hasattr(self, 'watch_path'):
            return
        
        try:
            existing = self.get_existing_audio_files(self.watch_path)
            if existing:
                self.log(f"📁 Found {len(existing)} file(s) to process", "info")
                for file_path in existing:
                    self.handler.process_existing(file_path)
        except Exception as e:
            self.log(f"⚠️  Scan error: {str(e)}", "warning")
    
    def get_existing_audio_files(self, watch_path):
        """Get list of existing audio files in watch folder."""
        existing = []
        all_files = list(watch_path.iterdir())
        
        for file_path in all_files:
            if file_path.is_file():
                ext = file_path.suffix.lower()
                if ext in self.config["extensions"]:
                    existing.append(file_path)
                else:
                    # Silently ignore non-audio files
                    pass
        
        return sorted(existing)
    
    def stop_watching(self):
        """Stop watching the folder."""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.running = False
            self.log("⏹️  Watcher stopped", "warning")
            return True
        return False
    
    def print_stats(self):
        """Print statistics."""
        print(f"\n{Colors.BOLD}📊 Statistics:{Colors.RESET}")
        print(f"  Uploaded: {Colors.GREEN}{self.stats['uploaded']}{Colors.RESET}")
        print(f"  Rejected: {Colors.YELLOW}{self.stats['rejected']}{Colors.RESET}")
        print(f"  Failed:   {Colors.RED}{self.stats['failed']}{Colors.RESET}")
        print(f"  Total:    {Colors.CYAN}{self.stats['total_mb']:.2f} MB{Colors.RESET}\n")


class AudioFileHandler(FileSystemEventHandler):
    """Handles new audio file events."""
    
    def __init__(self, client, server_config):
        self.client = client
        self.server_config = server_config
        self.processing = set()
        self.processed = set()  # Track already uploaded files
    
    def on_created(self, event):
        """Handle new file creation."""
        self._handle_file_event(event)
    
    def on_modified(self, event):
        """Handle file modification (catches files still being written)."""
        self._handle_file_event(event)
    
    def _handle_file_event(self, event):
        """Process file event."""
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        file_ext = file_path.suffix.lower()
        
        # Check if it's an audio file
        if file_ext not in self.client.config["extensions"]:
            return
        
        # Skip if already processed or currently processing
        file_key = str(file_path)
        if file_key in self.processing or file_key in self.processed:
            return
        
        self.processing.add(file_key)
        
        # Process file
        self._upload_file(file_path)
    
    def process_existing(self, file_path):
        """Process an existing file (called from scan loop)."""
        file_key = str(file_path)
        if file_key in self.processing or file_key in self.processed:
            return
        
        self.processing.add(file_key)
        self._upload_file(file_path)
    
    def _upload_file(self, file_path):
        """Upload file after stability check."""
        file_key = str(file_path)
        
        try:
            # Check if file still exists
            if not file_path.exists():
                self.client.log(f"⏭️  Skipping: {file_path.name} (file not found)", "info")
                return
            
            # Get stability settings
            check_interval = self.server_config['filesize_check_ms'] / 1000.0
            stability_window = self.server_config['stability_window_ms'] / 1000.0
            max_wait_seconds = 300
            
            # Wait for file stability
            self.client.log(f"📊 Monitoring: {file_path.name} (stability: {stability_window}s)", "info")
            prev_size = -1
            stable_start = None
            elapsed = 0
            
            while elapsed < max_wait_seconds:
                try:
                    if not file_path.exists():
                        self.client.log(f"⏭️  File removed: {file_path.name}", "info")
                        return
                    
                    curr_size = file_path.stat().st_size
                except (OSError, FileNotFoundError):
                    self.client.log(f"⏭️  File unavailable: {file_path.name}", "info")
                    return
                
                if curr_size == prev_size and curr_size > 0:
                    if stable_start is None:
                        stable_start = time.time()
                    
                    stable_duration = time.time() - stable_start
                    
                    if stable_duration >= stability_window:
                        break
                else:
                    if prev_size >= 0:
                        self.client.log(f"📈 Growing: {file_path.name} ({curr_size:,} bytes)", "info")
                    prev_size = curr_size
                    stable_start = None
                
                time.sleep(check_interval)
                elapsed += check_interval
            
            if elapsed >= max_wait_seconds:
                self.client.log(f"⏱️  Timeout: {file_path.name} exceeded {max_wait_seconds}s", "warning")
                return
            
            # Final existence check before rejection/upload
            if not file_path.exists():
                self.client.log(f"⏭️  File removed before upload: {file_path.name}", "info")
                return
            
            # Check rejection filters before uploading
            rejection_reason = self.client.check_rejection(file_path, self.server_config)
            if rejection_reason:
                self.client.log(f"❌ Rejected: {file_path.name} ({rejection_reason})", "warning")
                self.client.stats["rejected"] += 1
                # Report to server so dashboard "Rejected" stat updates (best-effort)
                reported = self.client.report_rejected(count=1)
                if not reported:
                    self.client.log("⚠️  Could not report rejection to server (will still skip file)", "warning")
                self.processed.add(file_key)  # Mark as processed
                
                # Delete rejected file if delete_after_upload is enabled
                if self.server_config.get("delete_after_upload", True):
                    try:
                        file_path.unlink()
                        self.client.log(f"🗑️  Deleted rejected file: {file_path.name}", "info")
                    except Exception as e:
                        self.client.log(f"⚠️  Failed to delete {file_path.name}: {str(e)}", "warning")
                return
            
            # Upload
            file_size_mb = prev_size / (1024 * 1024)
            self.client.log(f"📤 Uploading: {file_path.name} ({file_size_mb:.2f} MB)", "info")
            success, message = self.client.upload_file(file_path)
            
            if success:
                self.client.log(f"✅ {file_path.name} uploaded successfully", "success")
                self.processed.add(file_key)  # Mark as processed
                
                # Delete local file if enabled
                if self.server_config.get("delete_after_upload", True):
                    try:
                        file_path.unlink()
                        self.client.log(f"🗑️  Deleted local file: {file_path.name}", "info")
                    except Exception as e:
                        self.client.log(f"⚠️  Failed to delete {file_path.name}: {str(e)}", "warning")
            else:
                self.client.log(f"❌ {file_path.name}: {message}", "error")
                
        except Exception as e:
            self.client.log(f"❌ Error: {file_path.name} - {str(e)}", "error")
        finally:
            self.processing.discard(str(file_path))


def interactive_login(client):
    """Interactive login prompt."""
    print(f"\n{Colors.BOLD}═══ ScanScribe Server Configuration ═══{Colors.RESET}\n")
    
    # Server URL is FIRST
    print(f"{Colors.BOLD}Step 1: Server URL{Colors.RESET}")
    server = input(f"Enter server URL [{client.config['server_url']}]: ").strip() or client.config['server_url']
    client.config['server_url'] = server
    
    print(f"\n{Colors.BOLD}Step 2: Login Credentials{Colors.RESET}")
    username = input("Username: ").strip()
    password = input("Password: ").strip()
    
    print()  # Blank line
    
    if client.login(username, password):
        client.config['username'] = username
        client.config['password'] = password
        client.save_config()
        return True
    
    return False


def interactive_menu(client):
    """Show interactive command menu."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}╔═══════════════════════════════════════╗{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}║          ScanScribe Client            ║{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}╚═══════════════════════════════════════╝{Colors.RESET}")
    print(f"{Colors.GREEN}✅ Connected: {client.config['username']}@{client.config['server_url']}{Colors.RESET}\n")
    
    while True:
        print(f"{Colors.BOLD}Commands:{Colors.RESET}")
        print(f"  {Colors.CYAN}1{Colors.RESET}. Start watching")
        print(f"  {Colors.CYAN}2{Colors.RESET}. Set watch folder")
        print(f"  {Colors.CYAN}3{Colors.RESET}. Change server URL")
        print(f"  {Colors.CYAN}4{Colors.RESET}. Toggle delete after upload {Colors.GRAY}[{'ON' if client.config.get('delete_after_upload', True) else 'OFF'}]{Colors.RESET}")
        print(f"  {Colors.CYAN}5{Colors.RESET}. View statistics")
        print(f"  {Colors.CYAN}6{Colors.RESET}. View config")
        print(f"  {Colors.CYAN}7{Colors.RESET}. Logout")
        print(f"  {Colors.CYAN}8{Colors.RESET}. Exit")
        
        choice = input(f"\n{Colors.BOLD}>{Colors.RESET} ").strip()
        
        if choice == "1":
            start_watching_interactive(client)
        elif choice == "2":
            set_watch_folder(client)
        elif choice == "3":
            change_server(client)
        elif choice == "4":
            toggle_delete_after_upload(client)
        elif choice == "5":
            client.print_stats()
        elif choice == "6":
            view_config(client)
        elif choice == "7":
            client.token = None
            print(f"\n{Colors.YELLOW}👋 Logged out{Colors.RESET}\n")
            break
        elif choice == "8":
            if client.running:
                client.stop_watching()
            print(f"\n{Colors.CYAN}👋 Goodbye!{Colors.RESET}\n")
            sys.exit(0)
        else:
            print(f"{Colors.RED}❌ Invalid choice{Colors.RESET}\n")


def start_watching_interactive(client):
    """Start watching with user confirmation."""
    watch_path = Path(client.config["watch_folder"])
    
    print(f"\n{Colors.BOLD}Watch Folder:{Colors.RESET} {watch_path}")
    
    if not watch_path.exists():
        print(f"{Colors.YELLOW}⚠️  Folder doesn't exist. Create it? (y/n):{Colors.RESET} ", end="")
        if input().lower() == 'y':
            watch_path.mkdir(parents=True, exist_ok=True)
            print(f"{Colors.GREEN}✅ Folder created{Colors.RESET}")
        else:
            return
    
    print(f"{Colors.CYAN}Starting watcher...{Colors.RESET}\n")
    client.start_watching()
    
    print(f"\n{Colors.BOLD}Watcher is running. Press Ctrl+C to stop.{Colors.RESET}\n")
    
    # Handle Ctrl+C
    def stop_handler(sig, frame):
        print(f"\n{Colors.YELLOW}Stopping watcher...{Colors.RESET}")
        client.stop_watching()
        client.print_stats()
        print()
        raise KeyboardInterrupt()
    
    signal.signal(signal.SIGINT, stop_handler)
    
    try:
        scan_counter = 0
        while client.running:
            time.sleep(1)
            scan_counter += 1
            # Periodic scan every 10 seconds for any missed files
            if scan_counter >= 10:
                client.scan_existing_files()
                scan_counter = 0
    except KeyboardInterrupt:
        pass


def set_watch_folder(client):
    """Set watch folder interactively."""
    print(f"\n{Colors.BOLD}Current folder:{Colors.RESET} {client.config['watch_folder']}")
    new_folder = input(f"New folder path (or press Enter to keep current): ").strip()
    
    if new_folder:
        client.config['watch_folder'] = new_folder
        client.save_config()
        print(f"{Colors.GREEN}✅ Watch folder updated{Colors.RESET}\n")
    else:
        print(f"{Colors.GRAY}No changes made{Colors.RESET}\n")


def change_server(client):
    """Change server URL and force re-login."""
    print(f"\n{Colors.BOLD}Current server:{Colors.RESET} {client.config['server_url']}")
    new_server = input(f"New server URL (or press Enter to keep current): ").strip()
    
    if new_server:
        client.config['server_url'] = new_server
        client.token = None  # Invalidate current token
        client.save_config()
        print(f"{Colors.GREEN}✅ Server URL updated{Colors.RESET}")
        print(f"{Colors.YELLOW}⚠️  You need to login again{Colors.RESET}\n")
        
        # Force re-login
        if interactive_login(client):
            print(f"{Colors.GREEN}✅ Successfully connected to new server{Colors.RESET}\n")
        else:
            print(f"{Colors.RED}❌ Failed to connect to new server{Colors.RESET}\n")
    else:
        print(f"{Colors.GRAY}No changes made{Colors.RESET}\n")


def toggle_delete_after_upload(client):
    """Toggle delete after upload setting."""
    current = client.config.get("delete_after_upload", True)
    new_value = not current
    
    client.config["delete_after_upload"] = new_value
    client.save_config()
    
    status = f"{Colors.GREEN}ON{Colors.RESET}" if new_value else f"{Colors.YELLOW}OFF{Colors.RESET}"
    print(f"\n✅ Delete after upload: {status}")
    
    if new_value:
        print(f"{Colors.GRAY}Files will be deleted from local folder after successful upload{Colors.RESET}\n")
    else:
        print(f"{Colors.GRAY}Files will remain in local folder after upload{Colors.RESET}\n")


def view_config(client):
    """Display current configuration."""
    print(f"\n{Colors.BOLD}Current Configuration:{Colors.RESET}")
    print(f"  Server:              {Colors.CYAN}{client.config['server_url']}{Colors.RESET}")
    print(f"  Username:            {Colors.CYAN}{client.config['username']}{Colors.RESET}")
    print(f"  Folder:              {Colors.CYAN}{client.config['watch_folder']}{Colors.RESET}")
    print(f"  Allowed formats:     {Colors.CYAN}{', '.join(client.config['extensions'])}{Colors.RESET}")
    delete_status = f"{Colors.GREEN}ON{Colors.RESET}" if client.config.get('delete_after_upload', True) else f"{Colors.YELLOW}OFF{Colors.RESET}"
    print(f"  Delete after upload: {delete_status}")
    print(f"  Config file:         {Colors.GRAY}{client.config_path}{Colors.RESET}\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="ScanScribe Client - Upload audio files to ScanScribe server"
    )
    parser.add_argument("--server", help="Server URL (e.g., http://192.168.10.120:8000)")
    parser.add_argument("--username", "-u", help="Username")
    parser.add_argument("--password", "-p", help="Password")
    parser.add_argument("--folder", "-f", help="Watch folder path")
    parser.add_argument("--config", help="Config file path", default=CONFIG_FILE)
    parser.add_argument("--no-interactive", action="store_true", help="Run in non-interactive mode")
    
    args = parser.parse_args()
    
    # Initialize client
    client = ScanScribeClient(Path(args.config))
    
    # Override config from args
    if args.server:
        client.config["server_url"] = args.server
    if args.folder:
        client.config["watch_folder"] = args.folder
    
    # Non-interactive mode (headless operation)
    if args.no_interactive:
        username = args.username or client.config.get("username")
        password = args.password or client.config.get("password")
        
        if not username or not password:
            print(f"{Colors.RED}❌ Username/password required for non-interactive mode{Colors.RESET}\n")
            return
        
        if not client.login(username, password):
            return
        
        # Non-interactive: auto-process existing files without prompt
        client.start_watching(prompt_existing=False)
        
        # Process any existing files automatically
        client.scan_existing_files()
        
        # Handle Ctrl+C gracefully
        def signal_handler(sig, frame):
            print(f"\n{Colors.YELLOW}Shutting down...{Colors.RESET}")
            client.stop_watching()
            client.print_stats()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        try:
            scan_counter = 0
            while True:
                time.sleep(1)
                scan_counter += 1
                # Periodic scan every 10 seconds for any missed files
                if scan_counter >= 10:
                    client.scan_existing_files()
                    scan_counter = 0
        except KeyboardInterrupt:
            signal_handler(None, None)
    
    # Interactive mode (default)
    else:
        # Check if first time or needs login
        if not client.config.get("username") or not client.config.get("password") or args.username or args.password:
            if not interactive_login(client):
                print(f"{Colors.RED}❌ Login failed. Exiting.{Colors.RESET}\n")
                return
        else:
            # Try auto-login with saved credentials
            print(f"\n{Colors.CYAN}Connecting to {client.config['server_url']}...{Colors.RESET}")
            if not client.login():
                print(f"{Colors.YELLOW}⚠️  Saved credentials invalid. Please login again.{Colors.RESET}")
                if not interactive_login(client):
                    print(f"{Colors.RED}❌ Login failed. Exiting.{Colors.RESET}\n")
                    return
        
        # Show interactive menu
        try:
            interactive_menu(client)
        except KeyboardInterrupt:
            print(f"\n{Colors.CYAN}👋 Goodbye!{Colors.RESET}\n")
            if client.running:
                client.stop_watching()
            sys.exit(0)


if __name__ == "__main__":
    main()
