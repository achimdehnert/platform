#!/usr/bin/env python
"""
Kill Django Server - Cross-platform robust server killer
Kills all processes on port 8000 (or specified port)
"""

import argparse
import platform
import subprocess
import sys


def kill_port_windows(port: int) -> bool:
    """Kill process on port (Windows)"""
    try:
        # Find process using port
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        for line in result.stdout.splitlines():
            if f":{port}" in line and "LISTENING" in line:
                parts = line.split()
                if parts:
                    pid = parts[-1]
                    try:
                        subprocess.run(["taskkill", "/F", "/PID", pid], check=True)
                        print(f"✅ Killed process {pid} on port {port}")
                        return True
                    except subprocess.CalledProcessError:
                        print(f"⚠️  Failed to kill process {pid}")
        
        print(f"ℹ️  No process found on port {port}")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def kill_port_unix(port: int) -> bool:
    """Kill process on port (Unix/Linux/Mac)"""
    try:
        result = subprocess.run(
            ["lsof", "-ti", f":{port}"],
            capture_output=True,
            text=True
        )
        
        pids = result.stdout.strip().split('\n')
        if pids and pids[0]:
            for pid in pids:
                try:
                    subprocess.run(["kill", "-9", pid], check=True)
                    print(f"✅ Killed process {pid} on port {port}")
                except subprocess.CalledProcessError:
                    print(f"⚠️  Failed to kill process {pid}")
            return True
        else:
            print(f"ℹ️  No process found on port {port}")
            return True
            
    except FileNotFoundError:
        print("⚠️  lsof not available, trying alternative...")
        try:
            result = subprocess.run(
                ["fuser", "-k", f"{port}/tcp"],
                capture_output=True,
                text=True
            )
            print(f"✅ Killed process on port {port}")
            return True
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Kill Django development server")
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to free (default: 8000)"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output"
    )
    
    args = parser.parse_args()
    
    print(f"💀 Killing process on port {args.port}...")
    
    system = platform.system()
    
    if system == "Windows":
        success = kill_port_windows(args.port)
    else:
        success = kill_port_unix(args.port)
    
    if success:
        print("✅ Port cleared successfully!")
        sys.exit(0)
    else:
        print("❌ Failed to clear port")
        sys.exit(1)


if __name__ == "__main__":
    main()
