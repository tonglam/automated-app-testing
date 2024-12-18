"""
Prerequisites checker for Pagoda App Automation.
This script verifies all required components are properly set up.
"""

import os
import sys
import subprocess
import logging
import time
from typing import Dict
import requests
import psutil
import socket
import shutil
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PrerequisitesChecker:
    def __init__(self) -> None:
        self.all_checks_passed = True
        self.required_packages: Dict[str, str | None] = {
            'Appium-Python-Client': None,
            'requests': None,
            'selenium': None,
            'mitmproxy': None
        }
        self.required_images = [
            os.path.join('assets', 'close_button.png'),
            os.path.join('assets', 'nationwide_delivery_icon.png')
        ]
        self.required_files = [
            os.path.join('src', 'pagoda.py'),
            os.path.join('src', 'api_searcher.py'),
            os.path.join('src', 'extract_products.py'),
            'requirements.txt'
        ]
        self.appium_process = None
        self.mitmproxy_process = None
        self.venv_path = ''
        self.venv_python = ''
        self.venv_pip = ''

    def _is_port_in_use(self, port):
        """Check if a port is in use"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', port)) == 0

    def _kill_process_on_port(self, port):
        """Kill any process running on the specified port"""
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                for conn in proc.connections('inet'):
                    if conn.laddr.port == port:
                        proc.kill()
                        logger.info(f"Killed process {proc.name()} using port {port}")
                        return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.Error):
                pass
        return False

    def check_venv(self):
        """Check if virtual environment exists and is properly set up"""
        logger.info("Checking virtual environment...")
        project_root = Path(__file__).parent.parent
        self.venv_path = str(project_root / 'venv')
        self.venv_python = str(project_root / 'venv' / 'Scripts' / 'python.exe')
        self.venv_pip = str(project_root / 'venv' / 'Scripts' / 'pip.exe')
        
        if not os.path.exists(self.venv_path):
            logger.error("❌ Virtual environment not found")
            self.all_checks_passed = False
            return False
            
        if not os.path.exists(self.venv_python):
            logger.error("❌ Python not found in virtual environment")
            self.all_checks_passed = False
            return False

        logger.info("✅ Virtual environment exists")
        return True

    def run_in_venv(self, cmd, args=None, check=True):
        """Run a command in the virtual environment"""
        if args is None:
            args = []
        
        if cmd == 'python':
            cmd_path = self.venv_python
        elif cmd == 'pip':
            cmd_path = self.venv_pip
        else:
            cmd_path = os.path.join(self.venv_path, 'Scripts', cmd)

        try:
            result = subprocess.run(
                [cmd_path] + args,
                capture_output=True,
                text=True,
                check=check
            )
            return result
        except subprocess.CalledProcessError as e:
            if check:
                raise
            return e.returncode

    def start_appium_server(self):
        """Start the Appium server."""
        logger.info("Starting Appium server...")
        try:
            # Kill any existing process using port 4723
            self._kill_process_on_port(4723)
            
            # Get the Appium path
            appium_path = os.path.expanduser("~\\AppData\\Roaming\\npm\\appium.cmd")
            
            # Start Appium server with image plugin enabled
            self.appium_process = subprocess.Popen(
                [appium_path, "--use-plugins", "images", "--log-level", "error"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            # Wait for server to start
            time.sleep(5)
            
            # Check if server started successfully
            try:
                response = requests.get('http://localhost:4723/status')
                if response.status_code == 200:
                    logger.info("✅ Appium server started successfully")
                    return True
            except requests.exceptions.ConnectionError:
                pass
            
            logger.error("❌ Failed to connect to Appium server")
            return False
                
        except Exception as e:
            logger.error(f"❌ Error checking Appium server: {str(e)}")
            return False

    def start_mitmproxy(self):
        """Start mitmproxy in regular mode"""
        logger.info("Starting mitmproxy...")
        try:
            # First, kill any existing mitmproxy processes
            self._kill_process_on_port(8080)
            
            # If we have a previous mitmproxy process, clean it up
            if self.mitmproxy_process:
                try:
                    self.mitmproxy_process.terminate()
                    self.mitmproxy_process.wait(timeout=5)
                except (subprocess.TimeoutExpired, Exception):
                    try:
                        self.mitmproxy_process.kill()
                    except Exception:
                        pass
                self.mitmproxy_process = None
            
            # Start mitmproxy with configuration for emulator
            mitmdump_path = os.path.join(self.venv_path, 'Scripts', 'mitmdump.exe')
            
            # Start mitmproxy in a new console window
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 7  # SW_SHOWMINNOACTIVE
            
            self.mitmproxy_process = subprocess.Popen(
                [
                    mitmdump_path,
                    "--listen-host", "0.0.0.0",  # Listen on all interfaces
                    "--listen-port", "8080",     # Use port 8080
                    "-w", "traffic.flow",        # Write output to traffic.flow
                    "--ssl-insecure",           # Allow SSL inspection
                    "--set", "block_global=false"  # Don't block any traffic
                ],
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NEW_CONSOLE  # Create a new console window
            )
            
            # Wait for mitmproxy to start
            startup_wait = 5
            time.sleep(startup_wait)
            
            # Check if process is still running
            if self.mitmproxy_process.poll() is not None:
                logger.error("❌ Mitmproxy process failed to start")
                return False
            
            # Now check if port is accessible
            max_retries = 30
            retry_interval = 1
            
            for i in range(max_retries):
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                try:
                    # Check both localhost and 0.0.0.0
                    for host in ['127.0.0.1', '0.0.0.0']:
                        result = sock.connect_ex((host, 8080))
                        if result == 0:
                            logger.info(f"✅ Mitmproxy started successfully and listening on {host}:8080")
                            sock.close()
                            return True
                except socket.error:
                    pass
                finally:
                    sock.close()
                    
                if i < max_retries - 1:  # Don't sleep on the last iteration
                    time.sleep(retry_interval)
            
            logger.error("❌ Failed to start mitmproxy")
            return False
            
        except Exception as e:
            logger.error(f"❌ Failed to start mitmproxy: {str(e)}")
            return False

    def prepare_for_pagoda(self):
        """Prepare all services for pagoda.py"""
        logger.info("\nPreparing environment for pagoda.py...")
        
        # Run all checks first
        if not self.run_all_checks():
            logger.error("❌ Prerequisites check failed. Please fix the issues before running pagoda.py")
            return False
            
        # Start required services
        if not self.start_appium_server():
            return False
            
        if not self.start_mitmproxy():
            return False
            
        logger.info("\n✅ All services are running and ready for pagoda.py")
        return True

    def check_python_version(self):
        """Check if Python version is 3.x"""
        logger.info("Checking Python version...")
        version = sys.version_info
        if version.major < 3:
            logger.error(f"❌ Python version {version.major}.{version.minor} detected. Python 3.x is required.")
            self.all_checks_passed = False
        else:
            logger.info(f"✅ Python version {version.major}.{version.minor} detected.")
        return version.major >= 3

    def check_python_packages(self) -> bool:
        """Check if required Python packages are installed in virtual environment"""
        logger.info("Checking required packages in virtual environment...")
        
        # Make sure we're in virtual environment
        if not self.check_venv():
            return False
        
        # Create a working copy of required packages
        required_packages: Dict[str, str | None] = dict(self.required_packages)
        
        # Get list of installed packages
        result = subprocess.run(
            [os.path.join(self.venv_path, 'Scripts', 'pip'), 'list'],
            capture_output=True,
            text=True,
            check=True
        )
        
        # Parse installed packages
        for line in result.stdout.split('\n')[2:]:  # Skip header lines
            if not line:
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            package, version = parts[:2]
            if package in required_packages:
                required_packages[package] = version
        
        # Check each required package
        all_installed = True
        for package, installed_version in required_packages.items():
            if installed_version is not None:
                logger.info(f"✅ Package {package} version {installed_version} is installed")
            else:
                logger.error(f"❌ Required package {package} is not installed in virtual environment")
                all_installed = False
                
                # Try to install missing package
                try:
                    logger.info(f"Installing {package}...")
                    subprocess.run(
                        [os.path.join(self.venv_path, 'Scripts', 'pip'), 'install', package],
                        check=True,
                        capture_output=True
                    )
                    logger.info(f"✅ Successfully installed {package}")
                except subprocess.CalledProcessError as e:
                    logger.error(f"❌ Failed to install {package}: {e.stderr.decode()}")
                    self.all_checks_passed = False
        
        return all_installed

    def check_required_files(self):
        """Check if all required files exist"""
        logger.info("Checking required files...")
        project_root = Path(__file__).parent.parent
        all_files_exist = True
        for file in self.required_files + self.required_images:
            file_path = project_root / file
            if not file_path.exists():
                logger.error(f"❌ Required file {file} is missing.")
                all_files_exist = False
                self.all_checks_passed = False
            else:
                logger.info(f"✅ File {file} exists.")
        return all_files_exist

    def check_adb_connection(self):
        """Check if ADB can connect to the emulator"""
        logger.info("Checking ADB connection to emulator...")
        try:
            result = subprocess.run(
                ['adb', 'connect', '127.0.0.1:7555'],
                capture_output=True,
                text=True,
                check=True
            )
            if 'connected' in result.stdout.lower():
                logger.info("✅ ADB successfully connected to emulator.")
                return True
            else:
                logger.error("❌ Failed to connect to emulator via ADB.")
                self.all_checks_passed = False
                return False
        except subprocess.CalledProcessError:
            logger.error("❌ ADB command failed. Make sure Android SDK is installed and ADB is in PATH.")
            self.all_checks_passed = False
            return False
        except FileNotFoundError:
            logger.error("❌ ADB command not found. Make sure Android SDK is installed and ADB is in PATH.")
            self.all_checks_passed = False
            return False

    def find_system_node(self):
        """Find system Node.js installation"""
        possible_paths = [
            os.path.join(os.environ.get('APPDATA', ''), '..', 'Local', 'Programs', 'node'),  # User install
            os.path.join(os.environ.get('ProgramFiles', ''), 'nodejs'),  # System install x64
            os.path.join(os.environ.get('ProgramFiles(x86)', ''), 'nodejs'),  # System install x86
            os.path.join(os.environ.get('APPDATA', ''), 'npm'),  # NPM global
        ]

        for base_path in possible_paths:
            node_exe = os.path.join(base_path, 'node.exe')
            npm_cmd = os.path.join(base_path, 'npm.cmd')
            if os.path.exists(node_exe) and os.path.exists(npm_cmd):
                return node_exe, npm_cmd

        # Try to find in PATH
        try:
            result = subprocess.run(['where', 'node'], capture_output=True, text=True, check=True)
            node_path = result.stdout.strip().split('\n')[0]
            result = subprocess.run(['where', 'npm'], capture_output=True, text=True, check=True)
            npm_path = result.stdout.strip().split('\n')[0]
            if os.path.exists(node_path) and os.path.exists(npm_path):
                return node_path, npm_path
        except subprocess.CalledProcessError:
            pass

        return None, None

    def install_node_in_venv(self):
        """Install Node.js in virtual environment"""
        logger.info("Installing Node.js in virtual environment...")
        
        # First check if system Node.js is available
        try:
            result = subprocess.run(
                ['node', '--version'],
                capture_output=True,
                text=True,
                check=True
            )
            system_node_version = result.stdout.strip()
            logger.info(f"Found system Node.js {system_node_version}")
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.error("❌ System Node.js not found. Please install Node.js from https://nodejs.org/")
            return False

        # Find Node.js installation
        system_node, system_npm = self.find_system_node()
        if not system_node or not system_npm:
            logger.error("❌ Could not find system Node.js installation files")
            return False

        venv_node = os.path.join(self.venv_path, 'Scripts', 'node.exe')
        venv_npm = os.path.join(self.venv_path, 'Scripts', 'npm.cmd')
        venv_node_modules = os.path.join(self.venv_path, 'node_modules')

        try:
            # Copy Node.js executable
            shutil.copy2(system_node, venv_node)
            
            # Create npm.cmd in Scripts directory that uses system npm with modified prefix
            npm_cmd_content = f'''@ECHO off
SETLOCAL
SET "NPM_CONFIG_PREFIX={self.venv_path}"
"{system_npm}" %*
ENDLOCAL
EXIT /b %errorlevel%
'''
            
            with open(venv_npm, 'w') as f:
                f.write(npm_cmd_content)
            
            # Create node_modules directory
            os.makedirs(venv_node_modules, exist_ok=True)
            
            logger.info("✅ Node.js and npm installed in virtual environment")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to install Node.js in virtual environment: {str(e)}")
            return False

    def install_appium(self):
        """Install Appium and required plugins in virtual environment."""
        try:
            logger.info("Installing Appium and plugins...")
            npm_path = os.path.join(self.venv_path, 'Scripts', 'npm.cmd')
            appium_path = os.path.join(self.venv_path, 'Scripts', 'appium.cmd')
            
            # Install Appium
            subprocess.run([npm_path, "install", "-g", "appium"], check=True)
            
            # Install OpenCV for image plugin
            subprocess.run([npm_path, "install", "-g", "@appium/opencv"], check=True)
            
            # Install and configure image plugin
            subprocess.run([appium_path, "plugin", "install", "images"], check=True)
            subprocess.run([appium_path, "plugin", "list", "--installed"], check=True)
            
            logger.info("✅ Appium and plugins installed successfully")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Failed to install Appium: {e.stderr if e.stderr else str(e)}")
            return False

    def check_appium_installation(self):
        """Check if Appium is installed."""
        try:
            # Check global Appium installation
            appium_path = os.path.expanduser("~\\AppData\\Roaming\\npm\\appium.cmd")
            subprocess.check_output([appium_path, "--version"], text=True)
            logger.info("✅ Appium is installed globally")
            return True
        except subprocess.CalledProcessError:
            logger.error("❌ Failed to check Appium installation: Please install Appium globally using 'npm install -g appium'")
            return False
        except Exception as e:
            logger.error(f"❌ Failed to check Appium installation: {str(e)}")
            return False

    def check_node_installation(self):
        """Check if Node.js is installed in virtual environment"""
        logger.info("Checking Node.js installation in virtual environment...")
        node_path = os.path.join(self.venv_path, 'Scripts', 'node.exe')
        npm_path = os.path.join(self.venv_path, 'Scripts', 'npm.cmd')
        
        if not os.path.exists(node_path) or not os.path.exists(npm_path):
            logger.info("Node.js not found in virtual environment, attempting to install...")
            return self.install_node_in_venv()

        try:
            result = subprocess.run(
                [node_path, '--version'],
                capture_output=True,
                text=True,
                check=True
            )
            logger.info(f"✅ Node.js {result.stdout.strip()} is installed in virtual environment")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.error("❌ Node.js check failed in virtual environment")
            self.all_checks_passed = False
            return False

    def check_appium_server(self):
        """Check if Appium server is installed and running"""
        logger.info("Checking Appium server and plugins...")
        
        # First check Node.js installation
        if not self.check_node_installation():
            return False
        
        # Then check Appium installation
        appium_path = os.path.join(self.venv_path, 'Scripts', 'appium.cmd')
        
        if not os.path.exists(appium_path):
            logger.info("Appium not found in virtual environment, attempting to install...")
            return self.install_appium()

        try:
            # Check Appium version
            result = subprocess.run(
                [appium_path, '--version'],
                capture_output=True,
                text=True,
                check=True
            )
            logger.info(f"✅ Appium {result.stdout.strip()} is installed")
            
            # Check if image plugin is installed
            result = subprocess.run(
                [appium_path, 'plugin', 'list', '--installed'],
                capture_output=True,
                text=True,
                check=True
            )
            
            if 'images' not in result.stdout:
                logger.info("Image plugin not found, installing...")
                return self.install_appium()
            else:
                logger.info("✅ Appium image plugin is installed")
            
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Failed to check Appium installation: {e.stderr if e.stderr else str(e)}")
            return False

    def check_mitmproxy(self):
        """Check if mitmproxy port is available"""
        logger.info("Checking mitmproxy port (8080)...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind(("127.0.0.1", 8080))
            logger.info("✅ Port 8080 is available for mitmproxy.")
            return True
        except socket.error:
            logger.info("✅ Port 8080 is in use (mitmproxy might be running).")
            return True
        finally:
            sock.close()

    def check_pagoda_app(self):
        """Check if Pagoda app is installed on the emulator"""
        logger.info("Checking Pagoda app installation...")
        try:
            result = subprocess.run(
                ['adb', 'shell', 'pm', 'list', 'packages', 'com.pagoda.buy'],
                capture_output=True,
                text=True,
                check=True
            )
            if 'com.pagoda.buy' in result.stdout:
                logger.info("✅ Pagoda app is installed on the emulator.")
                return True
            else:
                logger.error("❌ Pagoda app is not installed on the emulator.")
                self.all_checks_passed = False
                return False
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.error("❌ Could not check Pagoda app installation. Make sure ADB is working.")
            self.all_checks_passed = False
            return False

    def run_all_checks(self):
        """Run all prerequisite checks"""
        logger.info("Starting prerequisites check...")
        
        checks = [
            self.check_venv(),
            self.check_python_version(),
            self.check_python_packages(),
            self.check_required_files(),
            self.check_adb_connection(),
            self.check_appium_installation(),
            self.check_mitmproxy(),
            self.check_pagoda_app()
        ]

        logger.info("\nPrerequisites Check Summary:")
        logger.info("=" * 50)
        if self.all_checks_passed:
            logger.info("✅ All checks passed! You can proceed with running pagoda.py")
        else:
            logger.error("❌ Some checks failed. Please fix the issues above before running pagoda.py")
        
        return self.all_checks_passed

    def cleanup(self):
        """Cleanup resources"""
        if self.appium_process:
            logger.info("Stopping Appium server...")
            self.appium_process.terminate()
            try:
                self.appium_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.appium_process.kill()
            logger.info("Appium server stopped")
        if self.mitmproxy_process:
            logger.info("Stopping mitmproxy...")
            self.mitmproxy_process.terminate()
            try:
                self.mitmproxy_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.mitmproxy_process.kill()
            logger.info("Mitmproxy stopped")

def main():
    checker = PrerequisitesChecker()
    try:
        if checker.prepare_for_pagoda():
            logger.info("\n🚀 You can now run pagoda.py")
        else:
            logger.error("\n❌ Failed to prepare environment for pagoda.py")
            sys.exit(1)
    except KeyboardInterrupt:
        logger.info("\nShutting down services...")
        checker.cleanup()
        sys.exit(0)

if __name__ == "__main__":
    main()
